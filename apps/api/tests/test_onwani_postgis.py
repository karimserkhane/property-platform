import json
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import psycopg
import pytest
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

if os.environ.get("LIWA_TEST_POSTGIS") != "1":
    pytest.skip("Onwani integration requires real PostGIS", allow_module_level=True)

from liwa.modules.catalog.models import Parcel  # noqa: E402
from liwa.modules.catalog.services import geometry_from_rings  # noqa: E402
from liwa.modules.evidence import onwani  # noqa: E402
from liwa.modules.evidence.models import (  # noqa: E402
    AuditEvent,
    Capture,
    IngestionRun,
    ParcelObservation,
    QuarantinedObservation,
)
from liwa.modules.evidence.services import LOCK_KEY, import_onwani  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def feature(oid=1, code="RT1_C1"):
    return {
        "attributes": {
            "OBJECTID": oid,
            "DISTRICTENG": "AL REEM ISLAND",
            "MUNICIPALITYENG": "ADM",
            "SectorNumber_PlotID": code,
        },
        "geometry": {"rings": [[[54.4, 24.5], [54.41, 24.5], [54.4, 24.51], [54.4, 24.5]]]},
    }


def responses(features):
    metadata = {
        "name": "PLOT",
        "geometryType": "esriGeometryPolygon",
        "extent": {"spatialReference": {"wkid": 4326}},
        "fields": [{"name": f} for f in onwani.FIELDS.split(",")],
    }
    ids = {"objectIds": [f["attributes"]["OBJECTID"] for f in features]}
    batch = {"features": features, "spatialReference": {"wkid": 4326}}
    now = datetime.now(UTC)
    receipt = {
        "url": onwani.BASE_URL,
        "http_status": 200,
        "fetched_started_at": now,
        "fetched_at": now,
        "etag": "",
        "last_modified_raw": "",
    }
    return [(json.dumps(d).encode(), receipt) for d in (metadata, ids, batch, ids)]


def run(features):
    with patch("liwa.modules.evidence.onwani.fetch", side_effect=responses(features)):
        return import_onwani(actor="integration-test")


def test_repeat_import_preserves_identity_and_audits_only_changes():
    first = run([feature()])
    parcel = Parcel.objects.get()
    assert first.summary["created"] == 1
    assert parcel.geometry.srid == 4326
    assert parcel.geometry.valid
    second = run([feature()])
    assert second.summary["unchanged"] == 1
    assert Parcel.objects.get().id == parcel.id
    assert AuditEvent.objects.count() == 1
    assert ParcelObservation.objects.count() == 2
    assert Capture.objects.count() == 8
    assert ParcelObservation.objects.filter(source_published_at__isnull=True).count() == 2
    changed = run([feature(code="RT1_C2")])
    assert changed.summary["updated"] == 1
    event = AuditEvent.objects.latest("id")
    assert event.before["code"] == "RT1_C1"
    assert event.after["code"] == "RT1_C2"
    assert event.parcel_revision == 2


def test_failed_collection_preserves_existing_catalogue_and_captures_error():
    run([feature()])
    bad = feature()
    bad["attributes"]["DISTRICTENG"] = "SWEIHAN"
    with (
        pytest.raises(onwani.SourceError),
        patch("liwa.modules.evidence.onwani.fetch", side_effect=responses([bad])),
    ):
        import_onwani(actor="integration-test")
    assert Parcel.objects.get().revision == 1
    assert IngestionRun.objects.filter(status="failed").count() == 1
    assert Capture.objects.count() == 7
    assert ParcelObservation.objects.count() == 1


def test_audit_failure_rolls_back_catalogue_and_observations_but_keeps_captures():
    with (
        patch("liwa.modules.evidence.onwani.fetch", side_effect=responses([feature()])),
        patch("liwa.modules.evidence.services.AuditEvent.objects.create", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        import_onwani(actor="integration-test")
    assert Parcel.objects.count() == 0
    assert ParcelObservation.objects.count() == 0
    assert Capture.objects.count() == 4
    assert IngestionRun.objects.get().status == "failed"


def test_missing_records_are_not_silently_applied():
    items = responses([feature(1), feature(2)])
    data = json.loads(items[2][0])
    data["features"] = [feature(1)]
    items[2] = (json.dumps(data).encode(), items[2][1])
    with (
        patch("liwa.modules.evidence.onwani.fetch", side_effect=items),
        pytest.raises(onwani.SourceError),
    ):
        import_onwani(actor="integration-test")
    assert Parcel.objects.count() == 0


def test_holes_and_disjoint_shells_are_preserved():
    outer = [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]
    hole = [[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]]
    second = [[5, 0], [6, 0], [6, 1], [5, 1], [5, 0]]
    geometry = geometry_from_rings([hole, second, outer])
    assert geometry.valid
    assert geometry.area == 16
    assert len(geometry) == 2


def test_invalid_geometry_is_quarantined_without_overwriting_previous_value():
    run([feature()])
    bad = feature()
    bad["geometry"]["rings"] = [[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]]
    result = run([bad, feature(2)])
    assert result.status == "quarantined"
    assert result.summary["quarantined"] == 1
    assert result.summary["created"] == 1
    assert Parcel.objects.get(source_record_id="1").revision == 1
    rejected = QuarantinedObservation.objects.get()
    assert rejected.source_record_id == "1"
    assert rejected.capture.run_id == result.id


def test_another_session_cannot_start_a_concurrent_import():
    with psycopg.connect(**connection.get_connection_params()) as other:
        other.execute("SELECT pg_advisory_lock(%s)", [LOCK_KEY])
        with pytest.raises(ValueError, match="already running"):
            import_onwani(actor="integration-test")
        assert IngestionRun.objects.count() == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"revision": 0},
        {"source_namespace": "   "},
        {"source_record_id": ""},
        {"geometry": MultiPolygon(srid=4326)},
        {"geometry": MultiPolygon(Polygon(((0, 0), (1, 1), (0, 1), (1, 0), (0, 0))), srid=4326)},
    ],
)
def test_database_rejects_invalid_parcel_even_when_services_are_bypassed(changes):
    run([feature()])
    parcel = Parcel.objects.get()
    with pytest.raises(IntegrityError), transaction.atomic():
        Parcel.objects.filter(pk=parcel.pk).update(**changes)
    parcel.refresh_from_db()
    assert parcel.revision == 1
    assert parcel.geometry.valid and not parcel.geometry.empty


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "unknown"},
        {"status": "succeeded", "finished_at": None},
        {"status": "running"},
        {"finished_at": datetime(2000, 1, 1, tzinfo=UTC)},
        {"actor": "   "},
    ],
)
def test_database_rejects_invalid_ingestion_lifecycle(changes):
    acquisition = run([feature()])
    with pytest.raises(IntegrityError), transaction.atomic():
        IngestionRun.objects.filter(pk=acquisition.pk).update(**changes)
    acquisition.refresh_from_db()
    assert acquisition.status == "succeeded"


@pytest.mark.parametrize(
    "field,value", [("http_status", 99), ("http_status", 600), ("content_sha256", "broken")]
)
def test_database_rejects_invalid_capture_metadata(field, value):
    run([feature()])
    capture = Capture.objects.first()
    with pytest.raises(IntegrityError), transaction.atomic():
        Capture.objects.filter(pk=capture.pk).update(**{field: value})


def test_database_rejects_reversed_capture_times():
    run([feature()])
    capture = Capture.objects.first()
    with pytest.raises(IntegrityError), transaction.atomic():
        Capture.objects.filter(pk=capture.pk).update(
            fetched_at=capture.fetched_started_at - timedelta(seconds=1)
        )


@pytest.mark.parametrize(
    "changes", [{"action": "deleted"}, {"parcel_revision": 0}, {"actor": ""}, {"reason": "   "}]
)
def test_database_rejects_invalid_audit_metadata(changes):
    run([feature()])
    event = AuditEvent.objects.get()
    with pytest.raises(IntegrityError), transaction.atomic():
        AuditEvent.objects.filter(pk=event.pk).update(**changes)


def test_integrity_migrations_preserve_existing_import_and_are_reversible():
    previous = [("catalog", "0001_initial"), ("evidence", "0002_quarantinedobservation")]
    current = [
        ("catalog", "0002_enforce_data_integrity"),
        ("evidence", "0003_enforce_data_integrity"),
    ]
    try:
        MigrationExecutor(connection).migrate(previous)
        acquisition = run([feature()])
        parcel = Parcel.objects.get()
        original_geometry = parcel.geometry.ewkb
        original_captures = list(Capture.objects.values_list("id", "content_sha256"))
        for targets in (current, previous):
            MigrationExecutor(connection).migrate(targets)
            assert Parcel.objects.get().id == parcel.id
            assert Parcel.objects.get().geometry.ewkb == original_geometry
            assert IngestionRun.objects.get().id == acquisition.id
            assert list(Capture.objects.values_list("id", "content_sha256")) == original_captures
            assert ParcelObservation.objects.count() == 1
            assert AuditEvent.objects.count() == 1
    finally:
        MigrationExecutor(connection).migrate(current)
