"""Real PostGIS capture replay, checksum safety and an honest table comparison."""

import hashlib
import json
import os
from datetime import UTC, datetime
from urllib.parse import urlencode
from uuid import uuid4

import pytest

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Capture rebuild requires real PostGIS", allow_module_level=True)

from property_platform.modules.catalog.models import Parcel  # noqa: E402
from property_platform.modules.evidence import onwani  # noqa: E402
from property_platform.modules.evidence import rebuild_archive as archive
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    IngestionRun,
    RowRevision,
    Source,
)

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def captured(root, value, url):
    payload = json.dumps(value).encode()
    digest = hashlib.sha256(payload).hexdigest()
    (root / "blobs").mkdir(exist_ok=True)
    (root / "blobs" / digest).write_bytes(payload)
    stamp = datetime(2026, 10, 1, tzinfo=UTC).isoformat()
    return {
        "sha256": digest,
        "byte_length": len(payload),
        "receipt": {
            "url": url,
            "fetched_at": stamp,
            "fetched_started_at": stamp,
            "http_status": 200,
            "acquisition_method": "scheduled_https_collect",
            "timestamp_basis": "collector_clock",
        },
    }


def test_rebuild_reparses_source_geometry_and_journals_the_new_ingestion(tmp_path, monkeypatch):
    feature = {
        "attributes": {
            "OBJECTID": 1,
            "DISTRICTENG": "AL REEM ISLAND",
            "MUNICIPALITYENG": "ADM",
            "SectorNumber_PlotID": "RT1_C1",
        },
        "geometry": {"rings": [[[54.4, 24.5], [54.41, 24.5], [54.4, 24.51], [54.4, 24.5]]]},
    }
    listing = {"objectIds": [1]}
    query = {
        "where": "DISTRICTENG = 'AL REEM ISLAND' AND MUNICIPALITYENG = 'ADM'",
        "returnIdsOnly": "true",
    }
    batch = {
        "where": query["where"],
        "objectIds": "1",
        "outFields": onwani.FIELDS,
        "returnGeometry": "true",
        "outSR": "4326",
    }
    metadata = {
        "name": "PLOT",
        "geometryType": "esriGeometryPolygon",
        "extent": {"spatialReference": {"wkid": 4326}},
        "fields": [{"name": f} for f in onwani.FIELDS.split(",")],
    }
    captures = [
        captured(tmp_path, value, onwani.BASE_URL + suffix)
        for value, suffix in (
            (metadata, "?f=pjson"),
            (listing, "/query?" + urlencode({"f": "json", **query})),
            (
                {"features": [feature], "spatialReference": {"wkid": 4326}},
                "/query?" + urlencode({"f": "json", **batch}),
            ),
            (listing, "/query?" + urlencode({"f": "json", **query})),
        )
    ]
    expected = archive.counts()
    expected["real_estate.parcel"] = expected["evidence.parcel_observation"] = 1
    manifest = {
        "version": 1,
        "snapshot_at": "2026-10-23T00:00:00+00:00",
        "expected": expected,
        "steps": [
            {
                "operation": "onwani",
                "scope": "al-reem-island",
                "run": "original",
                "captures": captures,
            }
        ],
        "scenes": [],
        "tiles": [],
        "omitted": [],
    }
    archive.write_json(tmp_path / "manifest.json", manifest)
    monkeypatch.setattr(onwani, "fetch", lambda *a, **k: pytest.fail("network forbidden"))
    result = archive.replay_archive(tmp_path, "integration-rebuild", str(uuid4()))
    assert result["ok"], (tmp_path / "report.json").read_text()
    assert Parcel.objects.get().geometry.valid
    assert Capture.objects.count() == 4
    assert all(c.fetched_at.year == 2026 and c.fetched_at.day == 1 for c in Capture.objects.all())
    assert all(c.ingested_at > c.fetched_at for c in Capture.objects.all())
    assert RowRevision.objects.filter(actor="integration-rebuild", table_name="parcel").exists()


def test_replay_rejects_missing_changed_or_unconsumed_bytes(tmp_path):
    item = captured(tmp_path, {}, "https://example.com/data?b=2&a=1")
    replay = archive.CaptureReplay(tmp_path, [item])
    with pytest.raises(ValueError, match="complete"):
        replay.assert_consumed()
    assert replay("https://example.com/data", {"a": 1, "b": 2})[0] == b"{}"
    replay.assert_consumed()
    with pytest.raises(ValueError, match="absent"):
        replay("https://example.com/data", {})
    with pytest.raises(ValueError, match="differs"):
        archive.CaptureReplay(tmp_path, [item])("https://other.example/data", {})
    (tmp_path / "blobs" / item["sha256"]).write_bytes(b"altered")
    with pytest.raises(ValueError, match="checksum"):
        archive.load_capture(tmp_path, item)
    with pytest.raises(ValueError, match="identity"):
        archive.load_capture(tmp_path, {**item, "sha256": "../private"})


def test_every_table_is_compared_and_unknown_tables_are_never_excused():
    result = archive.compare_tables(
        {"real_estate.parcel": 2, "evidence.row_revision": 20, "evidence.history_exclusion": 1},
        {
            "real_estate.parcel": 1,
            "evidence.row_revision": 50,
            "evidence.history_exclusion": 0,
            "evidence.unknown": 0,
        },
    )
    by_table = {row["table"]: row for row in result}
    assert by_table["real_estate.parcel"]["policy"] == "exact"
    assert not by_table["real_estate.parcel"]["matches"]
    assert by_table["evidence.unknown"]["policy"] == "exact"
    assert not by_table["evidence.unknown"]["matches"]
    assert by_table["evidence.row_revision"]["policy"] == "new_audit"
    assert by_table["evidence.history_exclusion"]["policy"] == "backup"


def test_geography_precedes_presentations_and_projects_without_reordering_versions():
    steps = [
        {"operation": operation, "version": version}
        for operation, version in (
            ("project_details", 1),
            ("map", 1),
            ("property_presentations", 1),
            ("osm_bootstrap", 1),
            ("project_details", 2),
            ("references", 1),
            ("onwani", 1),
        )
    ]
    result = archive.ordered_steps(steps)
    assert [s["operation"] for s in result] == [
        "onwani",
        "map",
        "osm_bootstrap",
        "references",
        "property_presentations",
        "project_details",
        "project_details",
    ]
    assert [s["version"] for s in result if s["operation"] == "project_details"] == [1, 2]


def test_export_does_not_mutate_the_source_and_counts_the_capture_snapshot(tmp_path):
    stamp = datetime(2026, 10, 1, tzinfo=UTC)
    source = Source.objects.create(
        key="dmt:onwani:smarthub:plot:adm:reem", name="Test", url=onwani.BASE_URL
    )
    run = IngestionRun.objects.create(source=source, actor="test", connector_version="test")
    run.status, run.finished_at = "succeeded", datetime.now(UTC)
    run.save(update_fields=["status", "finished_at"])
    Capture.objects.create(
        run=run,
        payload=b"{}",
        url=onwani.BASE_URL,
        http_status=200,
        fetched_at=stamp,
        fetched_started_at=stamp,
        byte_length=2,
        content_sha256=hashlib.sha256(b"{}").hexdigest(),
    )
    before = archive.counts()
    archive.export_archive(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert archive.counts() == before == manifest["expected"]
    assert len(manifest["steps"]) == 1
    archived = manifest["steps"][0]["captures"][0]
    assert archive.load_capture(tmp_path, archived)[0] == b"{}"


def test_historical_unavailable_reference_is_replayed_as_unavailable(tmp_path):
    from property_platform.modules.evidence.models import ResearchReference
    from property_platform.modules.evidence.orchestration import (
        reference_identity,
        reference_registry,
    )

    url = reference_registry("al-reem-island")[0]["url"]
    item = captured(tmp_path, {}, url)
    item["receipt"]["http_status"] = 404
    expected = archive.counts()
    expected["evidence.research_reference"] = 1
    archive.write_json(
        tmp_path / "manifest.json",
        {
            "version": 1,
            "snapshot_at": "2026-10-23T00:00:00+00:00",
            "expected": expected,
            "steps": [
                {
                    "operation": "references",
                    "scope": f"al-reem-island:{reference_identity(url)}",
                    "run": "original-unavailable",
                    "original_status": "failed",
                    "captures": [item],
                }
            ],
            "scenes": [],
            "tiles": [],
            "omitted": [],
        },
    )
    result = archive.replay_archive(tmp_path, "integration-rebuild", str(uuid4()))
    assert result["ok"]
    assert not ResearchReference.objects.get().available
    assert Capture.objects.get().http_status == 404
