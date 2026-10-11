import json
import os
from datetime import UTC, datetime, timedelta
from io import StringIO
from unittest.mock import patch

import psycopg
import pytest
from django.apps import apps
from django.core.management import call_command
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

if os.environ.get("LIWA_TEST_POSTGIS") != "1":
    pytest.skip("Onwani integration requires real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import MultiPolygon, Polygon  # noqa: E402

from liwa.modules.catalog.models import Parcel  # noqa: E402
from liwa.modules.catalog.services import geometry_from_rings  # noqa: E402
from liwa.modules.evidence import onwani  # noqa: E402
from liwa.modules.evidence.models import (  # noqa: E402
    AuditEvent,
    Capture,
    IngestionRun,
    ParcelObservation,
    QuarantinedObservation,
    Source,
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
        ("catalog", "0003_real_estate_schema"),
        ("evidence", "0004_evidence_schema"),
    ]
    try:
        acquisition = run([feature()])
        parcel = Parcel.objects.get()
        original_geometry = parcel.geometry.ewkb
        original_captures = list(Capture.objects.values_list("id", "content_sha256"))
        for targets in (previous, current, previous, current):
            executor = MigrationExecutor(connection)
            executor.migrate(targets)
            historical = executor.loader.project_state(targets).apps
            parcel_model = historical.get_model("catalog", "Parcel")
            assert parcel_model.objects.get().id == parcel.id
            assert parcel_model.objects.get().geometry.ewkb == original_geometry
            assert (
                historical.get_model("evidence", "IngestionRun").objects.get().id == acquisition.id
            )
            assert (
                list(
                    historical.get_model("evidence", "Capture").objects.values_list(
                        "id", "content_sha256"
                    )
                )
                == original_captures
            )
            assert historical.get_model("evidence", "ParcelObservation").objects.count() == 1
            assert historical.get_model("evidence", "AuditEvent").objects.count() == 1
    finally:
        MigrationExecutor(connection).migrate(current)


def test_schema_move_supports_introspection_serialization_flush_and_sequences():
    run([feature()])
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT n.nspname, c.relname FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE c.oid IN ('parcel'::regclass, 'capture'::regclass) ORDER BY c.relname"
        )
        assert cursor.fetchall() == [("evidence", "capture"), ("real_estate", "parcel")]
        cursor.execute(
            "SELECT to_regclass('public.catalog_parcel'), to_regclass('public.evidence_capture')"
        )
        assert cursor.fetchone() == (None, None)
        assert "parcel" in connection.introspection.table_names(cursor)
        assert "capture" in connection.introspection.table_names(cursor)
        constraints = connection.introspection.get_constraints(cursor, "parcel_observation")
        assert any(c["foreign_key"] == ("parcel", "id") for c in constraints.values())
    assert Parcel.objects.filter(geometry__intersects=Parcel.objects.get().geometry).count() == 1
    serialized = StringIO()
    call_command("dumpdata", "catalog", "evidence", stdout=serialized)
    assert any(obj["model"] == "catalog.parcel" for obj in json.loads(serialized.getvalue()))
    inspected = StringIO()
    call_command("inspectdb", "parcel", "capture", stdout=inspected)
    assert "MultiPolygonField" in inspected.getvalue()
    call_command("flush", interactive=False, verbosity=0)
    assert Parcel.objects.count() == Capture.objects.count() == 0
    assert run([feature()]).summary["created"] == 1
    assert Source.objects.get().pk == 1
    assert Capture.objects.first().pk == 1


def test_schema_collision_rolls_back_evidence_move_and_can_be_resumed():
    previous = [
        ("catalog", "0002_enforce_data_integrity"),
        ("evidence", "0003_enforce_data_integrity"),
    ]
    current = [("catalog", "0003_real_estate_schema"), ("evidence", "0004_evidence_schema")]
    acquisition = run([feature()])
    parcel_id = Parcel.objects.get().pk
    blocker_created = False
    try:
        MigrationExecutor(connection).migrate(previous)
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE public.capture (id bigint)")
        blocker_created = True
        with pytest.raises(DatabaseError, match="would be shadowed"):
            MigrationExecutor(connection).migrate(current)
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM public.evidence_capture")
            assert cursor.fetchone()[0] == 4
            cursor.execute("SELECT to_regclass('evidence.source')")
            assert cursor.fetchone()[0] is None
            cursor.execute("DROP TABLE public.capture")
        blocker_created = False
        MigrationExecutor(connection).migrate(current)
        assert Parcel.objects.get().pk == parcel_id
        assert IngestionRun.objects.get().pk == acquisition.pk
        assert Capture.objects.count() == 4
    finally:
        if blocker_created:
            with connection.cursor() as cursor:
                cursor.execute("DROP TABLE public.capture")
        MigrationExecutor(connection).migrate(current)


def test_domain_tables_have_unique_names_and_their_owned_schema():
    names = []
    with connection.cursor() as cursor:
        for label, schema in [("catalog", "real_estate"), ("evidence", "evidence")]:
            for model in apps.get_app_config(label).get_models():
                if not model._meta.managed:
                    continue
                name = model._meta.db_table
                names.append(name)
                cursor.execute(
                    "SELECT n.nspname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE c.oid = to_regclass(%s)",
                    [name],
                )
                assert cursor.fetchone() == (schema,), name
    assert len(names) == len(set(names))
