"""Portable acquisition protocol checks; no network, Django setup or database."""

import base64
import gzip
import hashlib
import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs

import httpx
import pytest
from property_platform.modules.evidence import map_sources, onwani
from property_platform.modules.evidence.property_protocol import validate_receipts

from property_platform_ingestion.collectors import (
    AcquisitionError,
    MapCollector,
    OnwaniCollector,
    ReferenceCollector,
    SourceHTTP,
    collect_property_receipts,
    precollect_map,
    precollect_onwani,
    precollect_reference,
)
from property_platform_ingestion.collectors.properties import property_urls
from property_platform_ingestion.collectors.references import selected_references

URL = "https://publisher.example/projects/one"
ROW = {"url": URL, "label": "Publisher — One", "kind": "developer"}


def client(urls, handler):
    def streaming_handler(request):
        response = handler(request)
        if response.is_stream_consumed:
            return httpx.Response(
                response.status_code,
                headers=response.headers,
                stream=httpx.ByteStream(response.content),
            )
        return response

    return SourceHTTP(
        urls, transport=httpx.MockTransport(streaming_handler), min_interval_seconds=0
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://publisher.example/project",
        "https://127.0.0.1/project",
        "https://[::1]/project",
        "https://user:secret@publisher.example/project",
        "https://publisher.example:8443/project",
        "https://publisher.internal/project",
        "https://localhost/project",
        URL + "#fragment",
        URL + "\n",
    ],
)
def test_unreviewable_source_urls_are_rejected_before_transport(url):
    with pytest.raises(AcquisitionError):
        client([url], lambda request: pytest.fail("Network must not be called"))


def test_unregistered_url_and_query_are_not_requested():
    with client([URL], lambda request: pytest.fail("Network must not be called")) as http:
        for url in [URL + "?next=https://evil.example", "https://evil.example/"]:
            with pytest.raises(AcquisitionError, match="not registered"):
                http.fetch(url, max_bytes=100)


def test_redirect_does_not_follow_location_to_another_host():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/secrets"})

    with client([URL], handler) as http, pytest.raises(AcquisitionError, match="redirects"):
        http.fetch(URL, max_bytes=100)
    assert calls == [URL]


def test_http_failure_bytes_and_utc_dates_are_preserved_without_hidden_retry():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, content=b"limit", headers={"ETag": '"revision"'})

    with client([URL], handler) as http:
        acquisition = http.fetch(URL, max_bytes=100)
        assert http.acquisitions == (acquisition,)
    receipt = acquisition.capture_receipt()
    assert len(calls) == 1
    assert acquisition.payload == b"limit"
    assert receipt["http_status"] == 429
    assert receipt["etag"] == '"revision"'
    assert receipt["fetched_started_at"].utcoffset().total_seconds() == 0
    assert receipt["fetched_started_at"] <= receipt["fetched_at"]
    assert receipt["acquisition_method"] == "scheduled_https_collect"
    with pytest.raises(AcquisitionError, match="HTTP 200"):
        acquisition.property_receipt()


def test_acquisition_journal_retains_complete_success_and_error_status_responses():
    urls = [URL, URL + "/unavailable"]
    with client(
        urls,
        lambda request: httpx.Response(
            200 if str(request.url) == URL else 406,
            content=b"source" if str(request.url) == URL else b"not acceptable",
        ),
    ) as http:
        success = http.fetch(urls[0], max_bytes=100)
        rejected = http.fetch(urls[1], max_bytes=100)
    assert http.acquisitions == (success, rejected)
    assert [item.payload for item in http.acquisitions] == [b"source", b"not acceptable"]
    assert rejected.capture_receipt()["fetched_at"] == rejected.fetched_at
    with pytest.raises(AttributeError):
        http.acquisitions = ()


def test_journal_never_fabricates_a_missing_transport_response():
    def handler(request):
        raise httpx.ReadTimeout("No response", request=request)

    with client([URL], handler) as http:
        with pytest.raises(AcquisitionError):
            http.fetch(URL, max_bytes=100)
    assert http.acquisitions == ()


def test_journal_never_marks_a_partial_stream_as_a_complete_capture():
    class Partial(httpx.SyncByteStream):
        def __iter__(self):
            yield b"partial"
            raise httpx.ReadTimeout("Incomplete body")

    with client([URL], lambda request: httpx.Response(200, stream=Partial())) as http:
        with pytest.raises(AcquisitionError, match="ReadTimeout"):
            http.fetch(URL, max_bytes=100)
    assert http.acquisitions == ()


@pytest.mark.parametrize("announced", [True, False])
def test_session_byte_budget_prevents_append_of_an_oversize_complete_capture(announced):
    def handler(request):
        return httpx.Response(
            200,
            headers={"Content-Length": "4"} if announced else {},
            stream=httpx.ByteStream(b"data"),
        )

    with SourceHTTP(
        [URL],
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
        max_session_bytes=6,
    ) as http:
        first = http.fetch(URL, max_bytes=10)
        with pytest.raises(AcquisitionError, match="session byte budget"):
            http.fetch(URL, max_bytes=10)
    assert http.acquisitions == (first,)
    assert sum(len(item.payload) for item in http.acquisitions) == 4


@pytest.mark.parametrize("limit", [0, 64 * 1024 * 1024 + 1, True, "64"])
def test_session_byte_budget_cannot_exceed_the_global_limit(limit):
    with pytest.raises(AcquisitionError, match="session byte budget"):
        SourceHTTP([URL], max_session_bytes=limit)


def test_journal_is_bounded_even_for_empty_actual_responses():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(204, stream=httpx.ByteStream(b""))

    with SourceHTTP(
        [URL],
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
        max_session_responses=2,
    ) as http:
        http.fetch(URL, max_bytes=10)
        http.fetch(URL, max_bytes=10)
        with pytest.raises(AcquisitionError, match="session response budget"):
            http.fetch(URL, max_bytes=10)
    assert len(calls) == len(http.acquisitions) == 2
    assert all(item.http_status == 204 and item.payload == b"" for item in http.acquisitions)


def test_domain_source_failure_passes_only_real_complete_responses_to_audit(monkeypatch):
    import django
    import property_platform.modules.evidence as evidence

    import property_platform_ingestion.collectors as collectors
    from property_platform_ingestion.domain import execute

    gateway = ModuleType("property_platform.modules.evidence.orchestration")
    gateway.execution_result = Mock(return_value=None)
    gateway.record_acquisition_failure = Mock(return_value={"status": "failed"})
    profiles = ModuleType("property_platform.modules.evidence.property_import")
    models = ModuleType("property_platform.modules.evidence.models")
    models.IngestionExecution = object
    db = ModuleType("django.db")
    db.connections = SimpleNamespace(close_all=Mock())
    monkeypatch.setattr(django, "setup", lambda: None)
    monkeypatch.setitem(sys.modules, "django.db", db)
    for name, module in (
        ("orchestration", gateway),
        ("property_import", profiles),
        ("models", models),
    ):
        monkeypatch.setitem(sys.modules, "property_platform.modules.evidence." + name, module)
        monkeypatch.setattr(evidence, name, module, raising=False)

    def handler(request):
        if request.url.host == "overpass-api.de":
            return httpx.Response(406, content=b"actual public error body")
        raise httpx.ReadTimeout("No completed mirror response", request=request)

    http = client(MapCollector.allowed_urls(), handler)
    monkeypatch.setattr(collectors, "SourceHTTP", lambda allowed_urls: http)
    request = {
        "operation": "map",
        "scope": "al-reem-island:osm",
        "execution_key": "a" * 64,
        "actor": "test",
    }
    assert execute(request) == {"status": "failed"}
    audit = gateway.record_acquisition_failure.call_args.kwargs
    assert audit["operation"] == "map"
    assert len(audit["received_acquisitions"]) == 1
    row = audit["received_acquisitions"][0]
    assert row["payload"] == b"actual public error body"
    assert row["receipt"]["http_status"] == 406
    assert row["receipt"]["fetched_started_at"] <= row["receipt"]["fetched_at"]
    assert row["receipt"]["fetched_at"].tzinfo is not None
    db.connections.close_all.assert_called_once()


@pytest.mark.parametrize("announced", [True, False])
def test_both_announced_and_streamed_oversize_responses_fail(announced):
    headers = {"Content-Length": "101"} if announced else {}
    response = httpx.Response(200, stream=httpx.ByteStream(b"x" * 101), headers=headers)
    with client([URL], lambda request: response) as http:
        with pytest.raises(AcquisitionError, match="byte budget"):
            http.fetch(URL, max_bytes=100)


def test_unrequested_response_encoding_is_rejected_before_decompression():
    payload = gzip.compress(b"x" * 1000)
    with client(
        [URL],
        lambda request: httpx.Response(200, content=payload, headers={"Content-Encoding": "gzip"}),
    ) as http:
        with pytest.raises(AcquisitionError, match="identity encoding"):
            http.fetch(URL, max_bytes=100)


def test_transport_timeout_has_no_stale_receipt_fallback():
    def handler(request):
        raise httpx.ReadTimeout("Untrusted response text", request=request)

    with client([URL], handler) as http:
        with pytest.raises(AcquisitionError, match="Source transport failed: ReadTimeout"):
            http.fetch(URL, max_bytes=100)


def test_total_elapsed_budget_is_checked_per_raw_network_chunk(monkeypatch):
    with client(
        [URL], lambda request: httpx.Response(200, stream=httpx.ByteStream(b"source"))
    ) as http:
        ticks = iter([0, 0, 121])
        monkeypatch.setattr(
            "property_platform_ingestion.collectors.http.time.monotonic", lambda: next(ticks)
        )
        with pytest.raises(AcquisitionError, match="total acquisition timeout"):
            http.fetch(URL, max_bytes=100)


def test_property_receipts_match_existing_protocol_hash_bytes_and_times():
    profiles = [{"source_url": URL, "photo_key": None}] * 2
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=b"project source bytes")

    with client(property_urls(profiles, {}), handler) as http:
        rows = collect_property_receipts(http, profiles, {})
    assert len(calls) == len(rows) == 1
    assert rows[0]["sha256"] == hashlib.sha256(b"project source bytes").hexdigest()
    assert base64.b64decode(rows[0]["payload"]) == b"project source bytes"
    assert validate_receipts(rows, {URL})[URL]["payload"] == b"project source bytes"


def test_property_collection_fails_whole_batch_when_one_source_fails():
    other = "https://publisher.example/projects/two"
    profiles = [{"source_url": url, "photo_key": None} for url in (URL, other)]
    with client(
        property_urls(profiles, {}),
        lambda request: httpx.Response(200 if str(request.url) == URL else 503, content=b"body"),
    ) as http:
        with pytest.raises(AcquisitionError, match="HTTP 200"):
            collect_property_receipts(http, profiles, {})


def test_property_receipt_budget_stops_collection_before_buffering_remaining_sources():
    urls = [URL + f"/{index}" for index in range(3)]
    profiles = [{"source_url": url, "photo_key": None} for url in urls]
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=b"project")

    with client(urls, handler) as http:
        with pytest.raises(AcquisitionError, match="receipt batch byte budget"):
            collect_property_receipts(http, profiles, {}, max_receipt_bytes=500)
    assert len(calls) == 2


def test_photo_bytes_are_not_importable_when_licence_claim_is_missing():
    licence_url = "https://commons.wikimedia.org/wiki/File:Example.jpg"
    image_url = "https://upload.wikimedia.org/wikipedia/commons/example.jpg"
    photo = {
        "source_url": licence_url,
        "image_url": image_url,
        "licence_code": "CC-BY-3.0",
        "licence_url": "https://creativecommons.org/licenses/by/3.0/",
        "author": "Photographer",
        "mime_type": "image/jpeg",
    }
    profiles = [{"source_url": URL, "photo_key": "example"}]
    photos = {"example": photo}
    with client(
        property_urls(profiles, photos),
        lambda request: httpx.Response(
            200, content=b"\xff\xd8\xffimage" if str(request.url) == image_url else b"No licence"
        ),
    ) as http:
        with pytest.raises(ValueError, match="author/licence"):
            collect_property_receipts(http, profiles, photos)


def test_reference_registry_selection_is_bounded_stable_and_exact():
    rows = [ROW, {"url": URL + "/media", "label": "Media", "kind": "media"}]
    assert selected_references(rows, kind="media") == [rows[1]]
    assert selected_references(rows, limit=1) == [ROW]
    with pytest.raises(AcquisitionError):
        selected_references(rows, limit=0)
    with pytest.raises(AcquisitionError, match="Duplicate"):
        selected_references([ROW, ROW])
    with client(ReferenceCollector.allowed_urls(rows), lambda request: httpx.Response(200)) as http:
        collector = ReferenceCollector(http, rows)
        with pytest.raises(AcquisitionError, match="exact registered"):
            collector.fetch({**ROW, "label": "Fake label"})
        with pytest.raises(AcquisitionError, match="not registered"):
            collector.fetch_url(URL + "?extra=1")


def test_map_transport_rejects_wider_area_and_unregistered_layers():
    with client(MapCollector.allowed_urls(), lambda request: pytest.fail("No request")) as http:
        collector = MapCollector(http)
        with pytest.raises(onwani.SourceError, match="registered area"):
            collector.fetch_url(map_sources.OSM_URL, {"data": "[out:json];nwr;out;"})
        base, where, _, _ = map_sources.LAYERS["district"]
        with pytest.raises(onwani.SourceError, match="territory"):
            collector.fetch_url(base + "/query", {"f": "json", "where": "1=1"})
        with pytest.raises(onwani.SourceError, match="not registered"):
            collector.fetch_url(base + "99", {"f": "pjson"})
        with pytest.raises(onwani.SourceError, match="metadata/query"):
            collector.fetch_url(base, {"f": "json", "where": where, "returnIdsOnly": "true"})


def test_osm_read_budget_accommodates_fixed_query_timeout_without_changing_other_sources():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={})

    with client(MapCollector.allowed_urls(), handler) as http:
        collector = MapCollector(http)
        collector.fetch_url(map_sources.OSM_URL, {"data": map_sources.OSM_QUERY})
        collector.fetch_url(map_sources.OSM_MIRROR, {"data": map_sources.OSM_QUERY})
        collector.fetch_url(map_sources.LAYERS["district"][0], {"f": "pjson"})
    assert [request.extensions["timeout"]["read"] for request in calls] == [60, 60, 30]


@pytest.mark.parametrize("timeout", [0, 121, float("nan"), "60", True])
def test_read_timeout_override_is_bounded_before_transport(timeout):
    with client([URL], lambda request: pytest.fail("No request")) as http:
        with pytest.raises(AcquisitionError, match="read timeout"):
            http.fetch(URL, max_bytes=100, read_timeout_seconds=timeout)


@pytest.mark.parametrize("ids", ["0", "1,1", "01", "1,2,", "1;DROP TABLE", ",".join(["1"] * 101)])
def test_onwani_transport_rejects_invalid_object_id_batches(ids):
    with client(OnwaniCollector.allowed_urls(), lambda request: pytest.fail("No request")) as http:
        with pytest.raises(onwani.SourceError, match="IDs"):
            OnwaniCollector(http).fetch(
                {
                    "where": onwani.WHERE,
                    "objectIds": ids,
                    "outFields": onwani.FIELDS,
                    "outSR": "4326",
                    "returnGeometry": "true",
                }
            )


def onwani_handler(*, changed=False, incomplete=False):
    listings = 0
    calls = []

    def handler(request):
        nonlocal listings
        calls.append(request)
        query = parse_qs(request.url.query.decode())
        if query == {"f": ["pjson"]}:
            data = {
                "name": "PLOT",
                "geometryType": "esriGeometryPolygon",
                "extent": {"spatialReference": {"wkid": 4326}},
                "fields": [{"name": name} for name in onwani.FIELDS.split(",")],
            }
        elif query.get("returnIdsOnly") == ["true"]:
            listings += 1
            data = {"objectIds": [1, 2] if listings == 1 or not changed else [1, 3]}
        else:
            data = {
                "spatialReference": {"wkid": 4326},
                "features": [
                    {"attributes": {"OBJECTID": oid}} for oid in ([1] if incomplete else [1, 2])
                ],
            }
        return httpx.Response(
            200, content=json.dumps(data).encode(), headers={"ETag": str(len(calls))}
        )

    return handler, calls


def test_onwani_stages_complete_snapshot_then_replays_two_same_url_captures_in_order():
    handler, calls = onwani_handler()
    with client(OnwaniCollector.allowed_urls(), handler) as http:
        replay = precollect_onwani(OnwaniCollector(http))
    assert len(calls) == 4
    with pytest.raises(AcquisitionError, match="complete acquisition"):
        replay.assert_consumed()
    replay.onwani()
    params = {"where": onwani.WHERE, "returnIdsOnly": "true"}
    _, first = replay.onwani(params)
    replay.onwani(
        {
            "where": onwani.WHERE,
            "objectIds": "1,2",
            "outFields": onwani.FIELDS,
            "returnGeometry": "true",
            "outSR": "4326",
        }
    )
    _, final = replay.onwani(params)
    assert first["url"] == final["url"]
    assert first["etag"] == "2" and final["etag"] == "4"
    assert first["fetched_at"] <= final["fetched_started_at"]
    replay.assert_consumed()
    with pytest.raises(AcquisitionError, match="exhausted"):
        replay.onwani(params)
    assert len(calls) == 4


@pytest.mark.parametrize("changed,incomplete", [(True, False), (False, True)])
def test_onwani_does_not_replay_incomplete_or_changing_coverage(changed, incomplete):
    handler, _ = onwani_handler(changed=changed, incomplete=incomplete)
    with client(OnwaniCollector.allowed_urls(), handler) as http:
        with pytest.raises(onwani.SourceError, match="coverage changed|Incomplete"):
            precollect_onwani(OnwaniCollector(http))


def test_precollection_total_budget_is_independent_of_per_response_budget():
    handler, _ = onwani_handler()
    with client(OnwaniCollector.allowed_urls(), handler) as http:
        with pytest.raises(AcquisitionError, match="total snapshot"):
            precollect_onwani(OnwaniCollector(http), max_total_bytes=30)


def test_osm_rate_limit_is_replayed_without_trying_mirror():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, content=b"rate limited")

    with client(MapCollector.allowed_urls(), handler) as http:
        replay = precollect_map(MapCollector(http), "osm")
    assert len(calls) == 1
    _, receipt = replay.map(map_sources.OSM_URL, {"data": map_sources.OSM_QUERY})
    assert receipt["http_status"] == 429
    replay.assert_consumed()


def test_official_map_stage_uses_registered_fields_and_replays_distinct_coverage_checks():
    base, where, geometry_type, fields = map_sources.LAYERS["community"]
    calls = []

    def handler(request):
        calls.append(request)
        query = parse_qs(request.url.query.decode())
        if query.get("f") == ["pjson"]:
            data = {
                "geometryType": geometry_type,
                "fields": [{"name": name} for name in fields.split(",")],
            }
        elif query.get("returnIdsOnly") == ["true"]:
            assert query["where"] == [where]
            data = {"objectIds": [12]}
        else:
            assert query["outFields"] == [fields]
            assert query["outSR"] == ["4326"]
            data = {
                "spatialReference": {"wkid": 4326},
                "features": [{"attributes": {"OBJECTID": 12}}],
            }
        return httpx.Response(200, json=data, headers={"ETag": str(len(calls))})

    with client(MapCollector.allowed_urls(), handler) as http:
        replay = precollect_map(MapCollector(http), "community")
    assert len(calls) == 4
    replay.map(base, {"f": "pjson"})
    params = {"f": "json", "where": where, "returnIdsOnly": "true"}
    _, first = replay.map(base + "/query", params)
    replay.map(
        base + "/query",
        {
            "f": "json",
            "where": where,
            "objectIds": "12",
            "outFields": fields,
            "outSR": 4326,
            "returnGeometry": "true",
        },
    )
    _, final = replay.map(base + "/query", params)
    assert first["etag"] == "2" and final["etag"] == "4"
    replay.assert_consumed()
    assert len(calls) == 4


def test_official_map_changed_schema_aborts_before_listing_or_database_replay():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"geometryType": "esriGeometryPoint", "fields": []})

    with client(MapCollector.allowed_urls(), handler) as http:
        with pytest.raises(onwani.SourceError, match="schema changed"):
            precollect_map(MapCollector(http), "district")
    assert len(calls) == 1


def test_osm_transport_failure_replays_failure_then_one_successful_mirror():
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.host == "overpass-api.de":
            raise httpx.ReadTimeout("Timeout", request=request)
        return httpx.Response(200, json={"elements": [{"id": 1}]})

    with client(MapCollector.allowed_urls(), handler) as http:
        replay = precollect_map(MapCollector(http), "osm")
    assert len(calls) == 2
    with pytest.raises(onwani.SourceError, match="ReadTimeout"):
        replay.map(map_sources.OSM_URL, {"data": map_sources.OSM_QUERY})
    _, receipt = replay.map(map_sources.OSM_MIRROR, {"data": map_sources.OSM_QUERY})
    assert receipt["http_status"] == 200
    replay.assert_consumed()


def test_reference_failure_replay_preserves_source_response_and_never_recollects():
    with client([URL], lambda request: httpx.Response(404, content=b"Unavailable")) as http:
        replay = precollect_reference(ReferenceCollector(http, [ROW]), URL)
    payload, receipt = replay.reference(URL)
    assert payload == b"Unavailable" and receipt["http_status"] == 404
    replay.assert_consumed()
