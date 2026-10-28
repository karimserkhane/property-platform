"""AD-SDI snapshot completeness and capture replay without network or database."""

import json
from types import SimpleNamespace

import httpx
import pytest
from property_platform.modules.evidence.maps import sdi_protocol as protocol
from test_collectors import client

from property_platform_ingestion.collectors import AcquisitionError, SourceHTTP
from property_platform_ingestion.collectors.sdi import precollect_sdi


def handler_for(*, changed=False, incomplete=False, commercial=2):
    calls = []

    def handler(request):
        params = request.url.params
        calls.append(dict(params))
        if request.url.path.endswith("/10"):
            data = {
                "name": "Plots",
                "geometryType": "esriGeometryPolygon",
                "extent": {"spatialReference": {"wkid": 4326}},
                "typeIdField": "PRIMARYUSEENG",
                "fields": [{"name": name} for name in protocol.FIELDS.split(",")],
                "types": [
                    {"id": commercial, "name": "Commercial"},
                    {"id": 13, "name": "Residential"},
                ],
            }
        elif params.get("returnIdsOnly") == "true":
            data = {"objectIds": [1, 2] if changed and len(calls) == 4 else [1]}
        else:
            data = {
                "spatialReference": {"wkid": 4326},
                "features": [] if incomplete else [{"attributes": {"OBJECTID": 1}}],
            }
        return httpx.Response(200, json=data)

    return calls, handler


def test_sdi_replays_both_listings_and_preserves_exact_capture_receipts():
    calls, handler = handler_for()
    with client([protocol.URL, protocol.URL + "/query"], handler) as http:
        replay = precollect_sdi(http, "al-maryah-island")
    assert len(calls) == 4
    assert calls[1] == calls[3]
    assert calls[2]["outFields"] == protocol.FIELDS
    assert calls[2]["where"] == protocol.where("al-maryah-island")
    for params in calls:
        base = protocol.URL if params == {"f": "pjson"} else protocol.URL + "/query"
        payload, receipt = replay.map(base, params)
        assert protocol.decode(payload)
        assert receipt["fetched_at"] >= receipt["fetched_started_at"]
        assert receipt["http_status"] == 200
    replay.assert_consumed()


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"changed": True}, "changed during acquisition"),
        ({"incomplete": True}, "Incomplete source batch"),
        ({"commercial": 20}, "subtype dictionary changed"),
    ],
)
def test_sdi_refuses_changing_incomplete_or_reclassified_snapshots(options, message):
    _, handler = handler_for(**options)
    with client([protocol.URL, protocol.URL + "/query"], handler) as http:
        with pytest.raises(protocol.SourceError, match=message):
            precollect_sdi(http, "al-maryah-island")


def test_district_scope_requests_only_its_reviewed_clause():
    calls, handler = handler_for()
    with client([protocol.URL, protocol.URL + "/query"], handler) as http:
        precollect_sdi(http, "aam:al-bateen")
    assert calls[1]["where"] == "MUNICIPALITYENG='AAM' AND DISTRICTENG='AL BATEEN'"
    assert calls[2]["where"] == calls[1]["where"]


def test_district_flow_runs_each_scope_and_reports_every_failure(monkeypatch):
    from property_platform_ingestion import flows
    from property_platform_ingestion.runtime import IngestionFailure

    seen = []

    def ingest(operation, scope, actor):
        seen.append((operation, scope, actor))
        if scope == "wrm:mzeerah":
            raise IngestionFailure({"status": "failed", "error": "SourceError"})
        return {"status": "succeeded"}

    monkeypatch.setattr(flows, "ingest_source", ingest)
    run = flows.sdi_district_parcels.fn
    with pytest.raises(IngestionFailure) as failure:
        run("WRM", ["wrm:mzeerah", "wrm:al-sila", "wrm:mzeerah"], "test")
    assert failure.value.result["failed_scopes"] == ["wrm:mzeerah"]
    assert seen == [("sdi_parcels", s, "test") for s in ("wrm:mzeerah", "wrm:al-sila")]
    with pytest.raises(ValueError, match="reviewed AD-SDI scopes"):
        run("WRM", ["adm:khalifa-city"], "test")
    assert run("AAM", ["aam:al-bateen"], "test") == {"aam:al-bateen": {"status": "succeeded"}}


def large_district(ids, padding):
    def handler(request):
        params = request.url.params
        if request.url.path.endswith("/10"):
            content = handler_for()[1](request).content
        elif params.get("returnIdsOnly") == "true":
            content = json.dumps({"objectIds": ids}).encode()
        else:
            batch = [int(value) for value in params["objectIds"].split(",")]
            content = json.dumps(
                {
                    "spatialReference": {"wkid": 4326},
                    "features": [{"attributes": {"OBJECTID": oid}} for oid in batch],
                    "padding": "x" * padding,
                }
            ).encode()
        return httpx.Response(200, stream=httpx.ByteStream(content))

    return handler


def test_district_session_holds_more_than_the_shared_64_mib_budget():
    # Al Faqa' (27/10/2026): 66.5 MB in 60 of its 74 batches of large rural plots.
    ids, padding = list(range(1, 7401)), 1024 * 1024
    urls = [protocol.URL, protocol.URL + "/query"]
    transport = httpx.MockTransport(large_district(ids, padding))
    with SourceHTTP(urls, transport=transport, min_interval_seconds=0) as http:
        with pytest.raises(AcquisitionError, match="byte budget"):
            precollect_sdi(http, "aam:al-faqa")
    with SourceHTTP(
        urls,
        transport=transport,
        min_interval_seconds=0,
        max_session_bytes=protocol.MAX_SESSION_BYTES,
        max_session_responses=protocol.MAX_RESPONSES,
    ) as http:
        replay = precollect_sdi(http, "aam:al-faqa")
    assert len(http.acquisitions) == 77
    assert sum(len(item.payload) for item in http.acquisitions) > 74 * padding
    replay.map(protocol.URL, {"f": "pjson"})


def test_district_imports_get_the_long_domain_timeout(monkeypatch):
    from property_platform_ingestion import flows
    from property_platform_ingestion.runtime import SDI_TIMEOUT, TIMEOUT

    timeouts = []
    monkeypatch.setattr(flows, "flow_run", SimpleNamespace(id="test-flow"))
    monkeypatch.setattr(flows, "get_run_logger", lambda: SimpleNamespace(info=lambda *a: None))
    monkeypatch.setattr(
        flows,
        "invoke_domain",
        lambda request, *, timeout: timeouts.append(timeout) or {"status": "succeeded"},
    )
    flows.ingest_source.fn("sdi_parcels", "adm:madinat-al-riyad", "test")
    flows.ingest_source.fn("onwani", "al-reem-island", "test")
    assert timeouts == [SDI_TIMEOUT, TIMEOUT]
    assert SDI_TIMEOUT > TIMEOUT
