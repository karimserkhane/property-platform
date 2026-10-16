"""Synthetic source structures and transport contracts, without network or database."""

import base64
import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from property_platform.modules.evidence.project_protocol import (
    MAX_CAPTURE_BYTES,
    extract_project_source,
    project_registry,
    project_urls,
    validate_project_receipts,
)

from property_platform_ingestion.collectors.http import AcquisitionError, SourceHTTP
from property_platform_ingestion.collectors.projects import collect_project_receipts


def project(slug):
    return next(row for row in project_registry() if row["slug"] == slug)


def html(body):
    return f"<!doctype html><html><head></head><body>{body}</body></html>".encode()


def source_html(row, source):
    if source["role"] == "terms":
        return html("<h1>Terms of Use</h1><p>Personal, non-commercial use.</p>")
    if source["parser"] == "aldar_project_v1":
        return json.dumps(
            {
                "data": {
                    "communityId": row["record_id"],
                    "projectName": row["name"],
                    "communityLocation": "Saadiyat Island"
                    if row["territory_id"] == "saadiyat-island"
                    else "Reem Island",
                    "totalUnits": 42,
                    "unitTypes": ["Apartment"],
                    "bedrooms": ["Studio", "2"],
                    "completionDate": "2029-06-30",
                }
            }
        ).encode()
    if source["parser"] == "official_project_v1":
        return html(
            f"<h1>{row['name']}</h1>"
            '<meta name="description" content="A reviewed project description">'
        )
    if source["parser"] == "reportage_offer_v1":
        return html(
            "<title>The District</title><span>Q2, 2029 Handover</span>"
            "<button>1 Bedroom</button><button>4 BDR Duplex</button>"
            "<script>const fake = 'Q4 2040 Handover';</script>"
        )
    if source["parser"] == "bloom_project_v1":
        place = {
            "@type": "Place",
            "name": row["name"],
            "url": source["url"],
            "description": "217 hotel apartments and 230 spacious residential units.",
            "amenityFeature": [{"@type": "LocationFeatureSpecification", "name": "Swimming Pool"}],
        }
        data = f'<script type="application/ld+json">{json.dumps(place)}</script>'
        return html(
            data + "<span>Studio, 1 Bathroom</span><span>3 Bedrooms, 3 Bathrooms</span>"
            '<a class="video-popup" href="https://vimeo.com/1038853770">Video</a>'
            '<video data-src="https://player.vimeo.com/file.mp4?signature=secret"></video>'
            '<a href="https://bloomholding.com/application/files/7416/4328/2984/Park_View_Brochure_Feb_2022.pdf">Brochure</a>'
        )
    count = 874 if row["slug"] == "the-district" else 622
    media = row["media_references"][0]["source_url"]
    if row["slug"] == "vista-3":
        media = media.replace("https://", "http://", 1)
    return html(
        f'<h3>{row["name"]}</h3><div class="counter-card-inner">'
        f"<h3>{count}</h3><p>Total Number of Units</p></div>"
        '<ul><li class="amenity-item">Large Swimming Pools</li>'
        '<li class="amenity-item">Gymnasium</li></ul>'
        "<button>2 Bedrooms Penthouse</button>"
        f'<a href="{media}">Download PDF</a>'
    )


def verified(row, source, payload=None):
    return {"url": source["url"], "payload": payload or source_html(row, source)}


def receipt(url, payload):
    now = datetime.now(UTC) - timedelta(seconds=1)
    return {
        "url": url,
        "payload": base64.b64encode(payload).decode(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "http_status": 200,
        "fetched_started_at": now.isoformat(),
        "fetched_at": now.isoformat(),
    }


def client(urls, handler):
    def streaming(request):
        response = handler(request)
        return httpx.Response(
            response.status_code,
            headers=response.headers,
            stream=httpx.ByteStream(response.content),
        )

    return SourceHTTP(urls, transport=httpx.MockTransport(streaming), min_interval_seconds=0)


def test_registry_is_territory_scoped_and_returned_without_shared_mutable_state():
    assert {row["slug"] for row in project_registry("al-reem-island")} >= {
        "the-district",
        "vista-3",
    }
    assert "park-view" in {row["slug"] for row in project_registry("saadiyat-island")}
    assert len(project_registry()) >= 53
    assert [row["slug"] for row in project_registry("saadiyat-island:park-view")] == ["park-view"]
    with pytest.raises(ValueError):
        project_registry("al-reem-island:park-view")
    row = project("park-view")
    row["developer"]["name"] = "Tampered"
    assert project("park-view")["developer"]["name"] == "Bloom Holding"
    with pytest.raises(ValueError, match="not registered"):
        project_registry("dubai")


def test_registry_scope_cannot_be_forged_or_expand_to_media():
    row = project("park-view")
    urls = project_urls([row])
    assert len(urls) == 2
    assert not any("vimeo" in url or url.endswith(".pdf") for url in urls)
    row["sources"][0]["url"] = "https://arbitrary.example/new-source"
    with pytest.raises(ValueError, match="exact reviewed"):
        project_urls([row])


@pytest.mark.parametrize("slug,count", [("the-district", 874), ("vista-3", 622)])
def test_reportage_adapter_extracts_same_typed_facts_for_separate_projects(slug, count):
    row = project(slug)
    source = row["sources"][0]
    result = extract_project_source(row, source, verified(row, source))
    assert result["total_units"] == count
    assert result["total_units_pointer"]
    assert result["summary"] == ""
    assert {item["code"] for item in result["amenities"]} == {"swimming_pool", "gym"}
    assert result["typologies"][0]["property_type"] == "penthouse"
    assert result["media"][0]["source_url"] == row["media_references"][0]["source_url"]
    assert result["media"][0]["rights_status"] == "reference_only"
    assert result["rights_status"] == "restricted"


def test_offer_preserves_quarter_precision_and_never_invents_a_delivery_day_or_price():
    row = project("the-district")
    source = row["sources"][1]
    result = extract_project_source(row, source, verified(row, source))
    assert result["handover"] == {
        "precision": "quarter",
        "year": 2029,
        "quarter": 2,
        "month": None,
        "day": None,
        "original_text": "Q2, 2029 Handover",
        "evidence_pointer": "visible-text:announced-handover",
    }
    assert {item["property_type"] for item in result["typologies"]} == {"apartment", "duplex"}
    assert "price" not in result and "availability" not in result


def test_conflicting_announced_handover_quarters_fail_instead_of_choosing_one():
    row = project("the-district")
    source = row["sources"][1]
    payload = source_html(row, source).replace(b"</body>", b"Q3 2030 Handover</body>")
    with pytest.raises(ValueError, match="unambiguous"):
        extract_project_source(row, source, verified(row, source, payload))


def test_bloom_extracts_residential_count_and_reference_video_without_signed_url_or_inventory():
    row = project("park-view")
    source = row["sources"][0]
    result = extract_project_source(row, source, verified(row, source))
    assert result["total_units"] == 230  # 217 hotel apartments is a distinct programme.
    assert [item["bedrooms"] for item in result["typologies"]] == [0, 3]
    video = next(item for item in result["media"] if item["kind"] == "video")
    assert video["source_url"] == "https://vimeo.com/1038853770"
    assert video["rights_status"] == "reference_only"
    assert "signature" not in json.dumps(result)
    assert "price" not in result and "availability" not in result


def test_unreviewed_media_links_are_never_promoted_to_references_or_downloads():
    row = project("park-view")
    source = row["sources"][0]
    payload = source_html(row, source).replace(
        b"</body>", b'<a href="https://evil.example/file.pdf">Brochure</a></body>'
    )
    result = extract_project_source(row, source, verified(row, source, payload))
    assert all("evil.example" not in item["source_url"] for item in result["media"])


@pytest.mark.parametrize("broken", [b"<html><h3>Wrong project</h3></html>", b"%PDF-not-html"])
def test_changed_source_identity_or_document_format_is_rejected(broken):
    row = project("the-district")
    with pytest.raises(ValueError):
        extract_project_source(row, row["sources"][0], verified(row, row["sources"][0], broken))


def test_terms_capture_is_required_but_not_mistaken_for_project_facts():
    row = project("park-view")
    source = row["sources"][1]
    assert extract_project_source(row, source, verified(row, source)) is None
    receipts = [receipt(item["url"], source_html(row, item)) for item in row["sources"]]
    assert len(validate_project_receipts(receipts, [row])) == 2
    with pytest.raises(ValueError, match="Incomplete"):
        validate_project_receipts(receipts[:1], [row])


def test_replay_checks_actual_bytes_hash_and_url_before_extraction():
    row = project("park-view")
    receipts = [receipt(item["url"], source_html(row, item)) for item in row["sources"]]
    damaged = copy.deepcopy(receipts)
    damaged[0]["payload"] = base64.b64encode(b"changed").decode()
    with pytest.raises(ValueError, match="hash or size"):
        validate_project_receipts(damaged, [row])
    damaged = copy.deepcopy(receipts)
    damaged[0]["url"] += "?extra=true"
    with pytest.raises(ValueError, match="Unexpected"):
        validate_project_receipts(damaged, [row])


def test_collector_fetches_each_registered_html_once_and_never_fetches_linked_media():
    rows = project_registry()
    fixtures = {
        source["url"]: source_html(row, source) for row in rows for source in row["sources"]
    }
    calls = []

    def handler(request):
        url = str(request.url)
        calls.append(url)
        return httpx.Response(200, content=fixtures[url])

    with client(project_urls(rows), handler) as http:
        receipts = collect_project_receipts(http, rows)
    assert len(receipts) == len(calls) == len(set(calls)) == len(project_urls(rows))
    assert all(url in project_urls(rows) for url in calls)
    assert len(validate_project_receipts(receipts, rows)) == len(project_urls(rows))


@pytest.mark.parametrize(
    "status,body", [(503, b"Unavailable"), (200, b"<html>Changed template</html>")]
)
def test_collector_rejects_incomplete_http_batch_and_changed_html_before_import(status, body):
    rows = project_registry("saadiyat-island")
    with client(project_urls(rows), lambda request: httpx.Response(status, content=body)) as http:
        with pytest.raises(ValueError):
            collect_project_receipts(http, rows)


def test_collector_response_and_receipt_budgets_are_enforced_before_unbounded_buffering():
    rows = project_registry("saadiyat-island")
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, content=b"x" * 200)

    with client(project_urls(rows), handler) as http:
        with pytest.raises(AcquisitionError, match="receipt batch byte budget"):
            collect_project_receipts(http, rows, max_receipt_bytes=100)
    assert len(calls) == 1
    source = rows[0]["sources"][0]
    with pytest.raises(ValueError, match="validated project receipt"):
        extract_project_source(
            rows[0], source, verified(rows[0], source, b"x" * (MAX_CAPTURE_BYTES + 1))
        )


def test_project_flow_uses_scoped_durable_gateway_without_archiving_restricted_media(monkeypatch):
    from property_platform_ingestion import flows

    calls = []

    def gateway(operation, scope, actor):
        calls.append((operation, scope, actor))
        return {"status": "succeeded", "summary": {"projects": 1}}

    gateway.with_options = lambda **kwargs: gateway
    monkeypatch.setattr(flows, "ingest_source", gateway)
    monkeypatch.setattr(flows, "archive_media", lambda *args: pytest.fail("No promoter copies"))
    result = flows.project_details.fn(territory="saadiyat-island", actor="reviewer")
    assert calls == [
        ("project_details", f"saadiyat-island:{row['slug']}", "reviewer")
        for row in project_registry("saadiyat-island")
    ]
    assert len(result) == len(calls)
    assert all(item["summary"]["projects"] == 1 for item in result)


def test_project_and_presentations_checkpoints_cannot_collide_for_one_prefect_run(tmp_path):
    from property_platform_ingestion.registry import execution_identity
    from property_platform_ingestion.storage import stored_property_receipt

    project_key = execution_identity("one-run", "project_details", "al-reem-island")
    presentation_key = execution_identity("one-run", "property_presentations", "al-reem-island")
    assert project_key != presentation_key
    original = [{"fetched_at": "original-project-source-time"}]
    assert stored_property_receipt(tmp_path, project_key, lambda: original) == original
    assert (
        stored_property_receipt(tmp_path, presentation_key, lambda: [{"different": True}])
        != original
    )
    assert (
        stored_property_receipt(
            tmp_path, project_key, lambda: pytest.fail("Replay must not acquire again")
        )
        == original
    )


def test_one_failed_project_does_not_prevent_other_project_imports(monkeypatch):
    from property_platform_ingestion import flows

    rows = project_registry("al-reem-island")
    calls = []

    def gateway(operation, scope, actor):
        calls.append(scope)
        if scope.endswith(":" + rows[0]["slug"]):
            raise flows.IngestionFailure({"status": "failed", "error": "SourceUnavailable"})
        return {"status": "succeeded"}

    gateway.with_options = lambda **kwargs: gateway
    monkeypatch.setattr(flows, "ingest_source", gateway)
    monkeypatch.setattr(flows, "get_run_logger", lambda: __import__("logging").getLogger(__name__))
    with pytest.raises(flows.IngestionFailure) as caught:
        flows.project_details.fn(territory="al-reem-island", actor="Karim")
    assert len(calls) == len(rows)
    assert caught.value.result["summary"] == {
        "succeeded": len(rows) - 1,
        "failed": [rows[0]["slug"]],
    }
