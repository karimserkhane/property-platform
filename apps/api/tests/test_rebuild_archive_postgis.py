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


def test_overpass_query_must_match_the_archived_query_exactly(tmp_path):
    query = "[out:json];way[building](24.4,54.3,24.5,54.4);out geom;"
    url = "https://overpass-api.de/api/interpreter"
    item = captured(tmp_path, {}, url + "?" + urlencode({"data": query}))
    archive.CaptureReplay(tmp_path, [item])(url, {"data": query})
    for different in (query + " ", "[out:json];node;out;"):
        with pytest.raises(ValueError, match="differs"):
            archive.CaptureReplay(tmp_path, [item])(url, {"data": different})
    missing_query = captured(tmp_path, {}, url)
    with pytest.raises(ValueError, match="differs"):
        archive.CaptureReplay(tmp_path, [missing_query])(url, {"data": query})


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


def test_identity_tables_excuse_only_reviewed_duplicate_repairs():
    def stats(active, superseded, repairs, fingerprint="same"):
        return {
            "active": active,
            "superseded": superseded,
            "reviewed_repairs": repairs,
            "active_fingerprint": fingerprint,
        }

    def compare(actual_identities, expected_identities=None):
        rows = archive.compare_tables(
            {"real_estate.parcel": 4},
            {"real_estate.parcel": 2},
            expected_identities or {"real_estate.parcel": stats(2, 2, 2)},
            {"real_estate.parcel": actual_identities},
        )
        return rows[0]

    repaired = compare(stats(2, 0, 0))
    assert repaired["policy"] == "identity"
    assert repaired["matches"]
    # Another active identity, a missing active row or an unreviewed duplicate is a gap.
    assert not compare(stats(2, 0, 0, "other"))["matches"]
    assert not compare(stats(1, 0, 0))["matches"]
    assert not compare(stats(2, 0, 0), {"real_estate.parcel": stats(2, 2, 1)})["matches"]
    # Without exported identity statistics the table stays an exact comparison.
    legacy = archive.compare_tables({"real_estate.parcel": 4}, {"real_estate.parcel": 2})
    assert legacy[0]["policy"] == "exact"
    assert not legacy[0]["matches"]


def test_identity_statistics_count_active_rows_and_reviewed_supersessions():
    from django.contrib.gis.geos import MultiPolygon, Polygon

    from property_platform.modules.evidence.models import ParcelSourceAlias

    stamp = datetime(2026, 10, 1, tzinfo=UTC)
    source = Source.objects.create(
        key="dmt:onwani:smarthub:plot:adm:reem", name="Test", url=onwani.BASE_URL
    )
    run = IngestionRun.objects.create(source=source, actor="test", connector_version="test")
    capture = Capture.objects.create(
        run=run,
        payload=b"{}",
        url=onwani.BASE_URL,
        http_status=200,
        fetched_at=stamp,
        fetched_started_at=stamp,
        byte_length=2,
        content_sha256=hashlib.sha256(b"{}").hexdigest(),
    )
    shape = MultiPolygon(
        Polygon(((54.4, 24.5), (54.41, 24.5), (54.4, 24.51), (54.4, 24.5))), srid=4326
    )
    values = {"source_namespace": source.key, "official_plot_id": "RT1_C1", "code": "RT1_C1"}
    values |= {"municipality": "ADM", "district": "AL REEM ISLAND", "geometry": shape}
    canonical = Parcel.objects.create(source_record_id="1", **values)
    before = archive.identities()["real_estate.parcel"]
    duplicate = Parcel.objects.create(source_record_id="2", superseded_by=canonical, **values)
    ParcelSourceAlias.objects.create(
        source_namespace=source.key,
        source_record_id="2",
        parcel=canonical,
        superseded_parcel=duplicate,
        capture=capture,
        actor="test",
        reason="Reviewed existing duplicate",
    )
    after = archive.identities()["real_estate.parcel"]
    assert after == before | {"superseded": 1, "reviewed_repairs": 1}
    assert after["active"] == 1


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


def test_a_shared_source_page_cannot_multiply_reviewed_presentation_targets(monkeypatch):
    from property_platform.modules.evidence import property_import

    url = "https://example.com/towers"
    first = {"source_url": url, "target": "building", "namespace": "osm:reem:osm", "record_id": "1"}
    second = {**first, "record_id": "2"}
    monkeypatch.setattr(
        property_import,
        "registry",
        lambda area: ([first, second], {}) if area == "al-reem-island" else ([], {}),
    )
    assert archive.reviewed_presentations(url, [first])[0] == [first]
    assert archive.reviewed_presentations(url, [second])[0] == [second]
    with pytest.raises(ValueError, match="target"):
        archive.reviewed_presentations(url, [{**first, "record_id": "unknown"}])


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


def test_repeated_query_keys_are_part_of_the_archived_request(tmp_path):
    url = "https://example.com/data"
    item = captured(tmp_path, {}, url + "?a=1&a=2")
    with pytest.raises(ValueError, match="differs"):
        archive.CaptureReplay(tmp_path, [item])(url, {"a": 2})
    archive.CaptureReplay(tmp_path, [item])(url + "?a=1&a=2", {})
    # A request parameter still replaces the same key carried by its base URL.
    single = captured(tmp_path, {}, url + "?a=2&b=1")
    archive.CaptureReplay(tmp_path, [single])(url + "?a=1", {"a": 2, "b": 1})


@pytest.mark.parametrize(
    ("original", "replayed", "ok"),
    [
        ("succeeded", "succeeded", True),
        ("quarantined", "quarantined", True),
        ("succeeded", "quarantined", False),
        ("quarantined", "succeeded", False),
        ("failed", "succeeded", False),
    ],
)
def test_a_status_different_from_the_original_run_fails_the_check(
    tmp_path, monkeypatch, original, replayed, ok
):
    monkeypatch.setattr(
        archive.orchestration,
        "execute_import",
        lambda **kwargs: {"status": replayed, "run_ids": []},
    )
    archive.write_json(
        tmp_path / "manifest.json",
        {
            "version": 1,
            "snapshot_at": "2026-10-23T00:00:00+00:00",
            "expected": archive.counts(),
            "steps": [
                {
                    "operation": "map",
                    "scope": "al-reem-island:osm",
                    "run": "original",
                    "original_status": original,
                    "captures": [],
                }
            ],
            "scenes": [],
            "tiles": [],
            "omitted": [],
        },
    )
    result = archive.replay_archive(tmp_path, "integration-rebuild", str(uuid4()))
    report = json.loads((tmp_path / "report.json").read_text())
    assert result["ok"] is ok
    assert result["diverged_steps"] == (0 if ok else 1)
    assert report["failed_steps"] == 0  # A divergence is reported apart from failed imports.
    if not ok:
        assert report["steps"][0]["diverged_from"] == original


def test_observation_counts_per_step_locate_a_difference_without_deciding_ok(tmp_path, monkeypatch):
    from django.contrib.gis.geos import Point

    from property_platform.modules.catalog.models import Place
    from property_platform.modules.evidence.models import MapObservation, QuarantinedObservation

    source = Source.objects.create(key="test:map", name="Test", url="https://example.com/map")
    run = IngestionRun.objects.create(source=source, actor="test", connector_version="test")
    stamp = datetime(2026, 10, 1, tzinfo=UTC)
    capture = Capture.objects.create(
        run=run,
        payload=b"{}",
        url=source.url,
        http_status=200,
        fetched_at=stamp,
        fetched_started_at=stamp,
        byte_length=2,
        content_sha256=hashlib.sha256(b"{}").hexdigest(),
    )
    place = Place.objects.create(
        source_namespace="test:place", source_record_id="1", geometry=Point(54.4, 24.5)
    )
    MapObservation.objects.create(
        place=place,
        capture=capture,
        source_record_id="1",
        source_url=source.url,
        raw_attributes={},
        record_sha256="b" * 64,
        mapping_version="test",
        action="created",
        target_revision=1,
    )
    QuarantinedObservation.objects.create(
        capture=capture, source_record_id="2", field_path="geometry", raw_attributes={}, reason="x"
    )
    rows = {"map_observation:place:created": 1, "quarantined_observation": 1}
    assert archive.run_rows([run.pk]) == rows
    monkeypatch.setattr(
        archive.orchestration,
        "execute_import",
        lambda **kwargs: {"status": "succeeded", "run_ids": [str(run.pk)]},
    )
    expected = {"map_observation:place:created": 3}
    archive.write_json(
        tmp_path / "manifest.json",
        {
            "version": 1,
            "snapshot_at": "2026-10-23T00:00:00+00:00",
            "expected": archive.counts(),
            "steps": [
                {
                    "operation": "map",
                    "scope": "al-reem-island:osm",
                    "run": "original",
                    "original_status": "succeeded",
                    "original_rows": expected,
                    "captures": [],
                }
            ],
            "scenes": [],
            "tiles": [],
            "omitted": [],
        },
    )
    result = archive.replay_archive(tmp_path, "integration-rebuild", str(uuid4()))
    report = json.loads((tmp_path / "report.json").read_text())
    # Table counts are equal here: the per-step difference is reported, not a failure.
    assert result["ok"] and result["row_differences"] == 1
    assert report["steps"][0]["rows"] == {"expected": expected, "actual": rows}


def _observed_run():
    """One run whose capture holds one place observation."""
    from django.contrib.gis.geos import Point

    from property_platform.modules.catalog.models import Place
    from property_platform.modules.evidence.models import MapObservation

    source = Source.objects.create(key="test:map", name="Test", url="https://example.com/map")
    run = IngestionRun.objects.create(source=source, actor="test", connector_version="test")
    stamp = datetime(2026, 10, 1, tzinfo=UTC)
    capture = Capture.objects.create(
        run=run,
        payload=b"{}",
        url=source.url,
        http_status=200,
        fetched_at=stamp,
        fetched_started_at=stamp,
        byte_length=2,
        content_sha256=hashlib.sha256(b"{}").hexdigest(),
    )
    place = Place.objects.create(
        source_namespace="test:place", source_record_id="1", geometry=Point(54.4, 24.5)
    )
    MapObservation.objects.create(
        place=place,
        capture=capture,
        source_record_id="1",
        source_url=source.url,
        raw_attributes={},
        record_sha256="b" * 64,
        mapping_version="test",
        action="created",
        target_revision=1,
    )
    return run


@pytest.mark.parametrize(
    ("variant", "ok"),
    [("reviewed", True), ("other_capture", False), ("other_observations", False)],
)
def test_only_a_reviewed_divergence_matching_its_later_run_is_counted_apart(
    tmp_path, monkeypatch, variant, ok
):
    reviewed_run = "d7b5f4bc-3390-4e62-85ef-90e765e842c0"
    review = archive.REVIEWED_DIVERGENCES[reviewed_run]
    run = _observed_run()
    monkeypatch.setattr(
        archive.orchestration,
        "execute_import",
        lambda **kwargs: {"status": "succeeded", "run_ids": [str(run.pk)]},
    )
    expected = archive.counts()
    # The original quarantined run wrote no observation; replay writes one more.
    expected["evidence.map_observation"] -= 1
    sha = review["captures"][0] if variant != "other_capture" else "0" * 64
    later = {"map_observation:place:created": 1 if variant != "other_observations" else 2}
    step = {"operation": "map", "scope": "al-reem-island:osm", "captures": []}
    archive.write_json(
        tmp_path / "manifest.json",
        {
            "version": 1,
            "snapshot_at": "2026-10-23T00:00:00+00:00",
            "expected": expected,
            "steps": [
                step
                | {
                    "run": reviewed_run,
                    "original_status": "quarantined",
                    "original_rows": {"quarantined_observation": 1},
                    "captures": [{"sha256": sha}],
                },
                step
                | {
                    "run": review["same_as_run"],
                    "original_status": "succeeded",
                    "original_rows": later,
                },
            ],
            "scenes": [],
            "tiles": [],
            "omitted": [],
        },
    )
    result = archive.replay_archive(tmp_path, "integration-rebuild", str(uuid4()))
    report = json.loads((tmp_path / "report.json").read_text())
    table = next(r for r in report["tables"] if r["table"] == "evidence.map_observation")
    assert result["ok"] is ok
    if ok:
        assert result["diverged_steps"] == 0 and result["reviewed_divergences"] == 1
        assert report["steps"][0]["reviewed_divergence"]["same_as_run"] == review["same_as_run"]
        assert table["reviewed_delta"] == 1 and table["matches"]
    else:
        # Another capture or other observations keep the plain divergence and table gap.
        assert result["diverged_steps"] == 1 and result["reviewed_divergences"] == 0
        assert report["steps"][0]["diverged_from"] == "quarantined"
        assert "reviewed_delta" not in table and not table["matches"]


def test_project_captures_outside_the_registry_are_reported_not_dropped(tmp_path):
    from property_platform.modules.evidence import project_protocol

    project = next(
        row
        for row in project_protocol.project_registry()
        if any(source["role"] != "terms" for source in row["sources"])
    )
    registered = next(source for source in project["sources"] if source["role"] != "terms")
    source = Source.objects.create(
        key=f"project:{project['slug']}", name="Test", url=registered["url"]
    )
    run = IngestionRun.objects.create(source=source, actor="test", connector_version="test")
    run.status, run.finished_at = "succeeded", datetime.now(UTC)
    run.save(update_fields=["status", "finished_at"])
    stamp = datetime(2026, 10, 1, tzinfo=UTC)
    for url in (registered["url"], registered["url"], "https://example.com/retired-source"):
        Capture.objects.create(
            run=run,
            payload=b"<html></html>",
            url=url,
            http_status=200,
            fetched_at=stamp,
            fetched_started_at=stamp,
            byte_length=13,
            content_sha256=hashlib.sha256(b"<html></html>").hexdigest(),
        )
    archive.export_archive(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert [len(step["captures"]) for step in manifest["steps"]] == [1]
    assert manifest["omitted"] == [
        {
            "source": source.key,
            "run": str(run.pk),
            "captures": 2,
            "reason": "Project capture not selected for replay: repeated or unregistered URL",
        }
    ]
