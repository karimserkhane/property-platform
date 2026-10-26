"""Source OBJECTIDs can change without creating a second canonical property."""

import json
import os
from datetime import UTC, datetime
from unittest.mock import patch

import psycopg
import pytest
from django.db import IntegrityError, connection, transaction

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Source alias integration requires real PostGIS", allow_module_level=True)

from test_onwani_postgis import feature, run  # noqa: E402

from property_platform.modules.catalog.models import AdministrativeArea, Parcel  # noqa: E402
from property_platform.modules.catalog.services import supersede_parcel  # noqa: E402
from property_platform.modules.evidence.maps import map_sources as map_protocol  # noqa: E402
from property_platform.modules.evidence.maps.identity_repair import (  # noqa: E402
    repair_source_identities,
    reverse_identity_decision,
)
from property_platform.modules.evidence.maps.identity_resolution import IdentityConflict  # noqa: E402
from property_platform.modules.evidence.maps.map_import import import_map_layer  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    AdministrativeAreaSourceAlias,
    AuditEvent,
    Capture,
    IngestionRun,
    MapObservation,
    ParcelObservation,
    ParcelSourceAlias,
)
from property_platform.modules.evidence.queries import (  # noqa: E402
    map_provenances,
    parcel_attributes,
    parcel_provenance,
)

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def plot(oid=1, *, code="RT1_C1", plot_id="100", land_use=None):
    value = feature(oid, code)
    value["attributes"]["PLOTID"] = plot_id
    if land_use:
        value["attributes"]["ELMS_LANDUSENAME_E"] = land_use
    return value


def duplicate_values(obj):
    return {
        field: getattr(obj, field)
        for field in (
            "official_plot_id",
            "code",
            "municipality",
            "district",
            "community",
            "land_use",
            "construction_status",
            "geometry",
        )
    }


def legacy_duplicate():
    run([plot()])
    canonical = Parcel.objects.get()
    newer = plot(101)
    newer["attributes"]["Permit_LastType"] = "Fresh permit source observation"
    # Reproduce the historic importer behaviour, without weakening the current guard.
    with patch(
        "property_platform.modules.evidence.maps.services.resolve_parcel", return_value=None
    ):
        acquisition = run([newer])
    duplicate = Parcel.objects.exclude(pk=canonical.pk).get()
    return canonical, duplicate, acquisition


def area_run(oid=1, *, name="RT1", district="57", changed_geometry=False):
    url, _, geometry_type, fields = map_protocol.LAYERS["community"]
    attrs = {
        "OBJECTID": oid,
        "COMMUNITYNAMEENG": name,
        "COMMUNITYNAMEARA": "القطاع",
        "DISTRICTID": district,
    }
    rings = [[[54.4, 24.5], [54.41, 24.5], [54.4, 24.51], [54.4, 24.5]]]
    if changed_geometry:
        rings[0][1][0] += 0.001
    meta = {"geometryType": geometry_type, "fields": [{"name": name} for name in fields.split(",")]}
    listing = {"objectIds": [oid]}
    batch = {
        "spatialReference": {"wkid": 4326},
        "features": [{"attributes": attrs, "geometry": {"rings": rings}}],
    }
    now = datetime.now(UTC)
    receipt = {
        "url": url,
        "http_status": 200,
        "fetched_started_at": now,
        "fetched_at": now,
        "etag": "",
        "last_modified_raw": "",
    }
    with patch(
        "property_platform.modules.evidence.maps.map_sources.fetch_url",
        side_effect=[
            (json.dumps(value).encode(), receipt) for value in (meta, listing, batch, listing)
        ],
    ):
        return import_map_layer(layer="community", actor="source-test")


def test_refresh_objectid_preserves_plot_uuid_identity_and_capture_history():
    run([plot()])
    canonical = Parcel.objects.get()
    refreshed = run([plot(101)])
    canonical.refresh_from_db()
    assert refreshed.summary["unchanged"] == 1 and refreshed.summary["created"] == 0
    assert Parcel.objects.count() == 1 and canonical.source_record_id == "1"
    alias = ParcelSourceAlias.objects.get()
    assert alias.parcel_id == canonical.id and alias.source_record_id == "101"
    assert alias.capture.run_id == refreshed.id and alias.superseded_parcel_id is None
    assert alias.active and alias.canonical_revision == canonical.revision
    assert set(ParcelObservation.objects.values_list("source_record_id", flat=True)) == {"1", "101"}
    assert Capture.objects.count() == 8 and AuditEvent.objects.count() == 1
    assert (
        parcel_provenance(parcel_id=canonical.id, source_key=canonical.source_namespace)[
            "retrieved_at"
        ]
        == alias.capture.fetched_at
    )


def test_persisted_alias_snapshot_includes_same_acquisition_catalogue_update():
    run([plot(land_use="Residential")])
    refreshed = run([plot(101, land_use="Commercial")])
    canonical, alias = Parcel.objects.get(), ParcelSourceAlias.objects.get()
    assert refreshed.summary["updated"] == 1
    assert canonical.revision == alias.canonical_revision == 2


def test_full_identity_composite_keeps_same_local_plot_number_in_distinct_sectors():
    run([plot(1, code="RT1_C1"), plot(2, code="RT2_C1")])
    before = set(Parcel.objects.values_list("pk", flat=True))
    refreshed = run([plot(101, code="RT1_C1"), plot(102, code="RT2_C1")])
    assert refreshed.summary["unchanged"] == 2 and refreshed.summary["created"] == 0
    assert set(Parcel.objects.values_list("pk", flat=True)) == before
    assert ParcelSourceAlias.objects.count() == 2


@pytest.mark.parametrize("use_alias", [False, True])
def test_reused_objectid_cannot_overwrite_another_official_plot(use_alias):
    run([plot()])
    if use_alias:
        run([plot(101)])
    with pytest.raises(IdentityConflict):
        run([plot(101 if use_alias else 1, plot_id="999")])
    assert Parcel.objects.get().official_plot_id == "100"
    assert IngestionRun.objects.latest("started_at").status == "failed"


def test_new_objectid_with_changed_geometry_requires_review():
    run([plot()])
    changed = plot(101)
    changed["geometry"]["rings"][0][1][0] += 0.001
    with pytest.raises(IdentityConflict):
        run([changed])
    assert Parcel.objects.count() == 1 and not ParcelSourceAlias.objects.exists()


def test_ambiguous_same_composite_is_not_merged_or_overwritten():
    run([plot()])
    canonical = Parcel.objects.get()
    Parcel.objects.create(
        source_namespace=canonical.source_namespace,
        source_record_id="2",
        **duplicate_values(canonical),
    )
    with pytest.raises(IdentityConflict):
        run([plot(101)])
    assert Parcel.objects.count() == 2 and not ParcelSourceAlias.objects.exists()


def test_repair_dryrun_application_and_repeat_keep_every_original_proof():
    canonical, duplicate, acquisition = legacy_duplicate()
    capture_ids = list(Capture.objects.values_list("pk", flat=True))
    observations = list(ParcelObservation.objects.values_list("pk", "parcel_id", "capture_id"))
    plan = repair_source_identities(run_id=acquisition.id, actor="reviewer")
    assert plan["candidates"] == 1 and plan["conflicts"] == 0 and not plan["applied"]
    duplicate.refresh_from_db()
    assert duplicate.superseded_by_id is None and not ParcelSourceAlias.objects.exists()
    applied = repair_source_identities(run_id=acquisition.id, actor="reviewer", apply=True)
    assert applied["applied"] and applied["candidates"] == 1
    duplicate.refresh_from_db()
    canonical.refresh_from_db()
    alias = ParcelSourceAlias.objects.get()
    assert duplicate.superseded_by_id == canonical.id
    assert alias.superseded_parcel_id == duplicate.id and alias.parcel_id == canonical.id
    assert alias.superseded_revision == duplicate.revision
    assert alias.actor == "reviewer" and alias.capture.run_id == acquisition.id
    assert (
        Parcel.objects.count() == 2
        and Parcel.objects.filter(superseded_by__isnull=True).count() == 1
    )
    assert list(Capture.objects.values_list("pk", flat=True)) == capture_ids
    assert (
        list(ParcelObservation.objects.values_list("pk", "parcel_id", "capture_id")) == observations
    )
    assert AuditEvent.objects.count() == 2
    assert (
        parcel_provenance(parcel_id=canonical.id, source_key=canonical.source_namespace)[
            "retrieved_at"
        ]
        == alias.capture.fetched_at
    )
    assert parcel_attributes(canonical.id)["Permit_LastType"] == "Fresh permit source observation"
    repeated = repair_source_identities(run_id=acquisition.id, actor="reviewer", apply=True)
    assert repeated["candidates"] == 0 and repeated["already_resolved"] == 1
    assert ParcelSourceAlias.objects.count() == 1
    assert run([plot(101)]).summary["unchanged"] == 1


def test_reversal_is_audited_idempotent_and_weekly_import_cannot_undo_it():
    canonical, duplicate, acquisition = legacy_duplicate()
    repair_source_identities(run_id=acquisition.id, actor="reviewer", apply=True)
    alias = ParcelSourceAlias.objects.get()
    preview = reverse_identity_decision(
        target="parcel",
        decision_id=alias.id,
        actor="another-reviewer",
        reason="Review identity",
        apply=False,
    )
    assert preview["active"] and not preview["applied"]
    reverse_identity_decision(
        target="parcel",
        decision_id=alias.id,
        actor="another-reviewer",
        reason="Review identity",
        apply=True,
    )
    alias.refresh_from_db()
    duplicate.refresh_from_db()
    assert not alias.active and alias.revoked_by == "another-reviewer" and alias.revoked_at
    assert duplicate.superseded_by_id is None
    old_reversal = alias.revoked_at
    reverse_identity_decision(
        target="parcel",
        decision_id=alias.id,
        actor="another-reviewer",
        reason="Repeat reversal",
        apply=True,
    )
    alias.refresh_from_db()
    assert alias.revoked_at == old_reversal
    with pytest.raises(IdentityConflict, match="revoked"):
        run([plot(101)])
    assert ParcelSourceAlias.objects.count() == 1
    # Explicit re-review creates a new decision; the revoked evidence stays immutable.
    repaired = repair_source_identities(run_id=acquisition.id, actor="new-reviewer", apply=True)
    assert repaired["candidates"] == 1
    assert ParcelSourceAlias.objects.count() == 2
    assert ParcelSourceAlias.objects.filter(active=True).count() == 1
    assert Parcel.objects.filter(superseded_by__isnull=True).get().id == canonical.id


def test_changed_catalogue_revision_blocks_silent_reversal():
    _, _, acquisition = legacy_duplicate()
    repair_source_identities(run_id=acquisition.id, actor="reviewer", apply=True)
    alias = ParcelSourceAlias.objects.get()
    run([plot(101, land_use="Commercial")])
    with pytest.raises(IdentityConflict, match="changed"):
        reverse_identity_decision(
            target="parcel", decision_id=alias.id, actor="reviewer", reason="Undo", apply=True
        )
    alias.refresh_from_db()
    assert alias.active


def test_reversal_busy_source_keeps_decision_and_releases_first_lock():
    canonical, duplicate, acquisition = legacy_duplicate()
    repair_source_identities(run_id=acquisition.id, actor="reviewer", apply=True)
    alias = ParcelSourceAlias.objects.get()
    with psycopg.connect(**connection.get_connection_params()) as other:
        other.execute("SELECT pg_advisory_lock(716548220)")
        with pytest.raises(IdentityConflict, match="running"):
            reverse_identity_decision(
                target="parcel", decision_id=alias.id, actor="reviewer", reason="Review", apply=True
            )
    alias.refresh_from_db()
    duplicate.refresh_from_db()
    assert alias.active and duplicate.superseded_by_id == canonical.id
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(716548219)")
        assert cursor.fetchone()[0] is True
        cursor.execute("SELECT pg_advisory_unlock(716548219)")


def test_administrative_refresh_requires_full_source_metadata_and_geometry():
    area_run()
    canonical = AdministrativeArea.objects.get()
    refreshed = area_run(101)
    assert refreshed.summary["unchanged"] == 1 and AdministrativeArea.objects.count() == 1
    alias = AdministrativeAreaSourceAlias.objects.get()
    assert alias.administrative_area_id == canonical.id and alias.capture.run_id == refreshed.id
    assert (
        map_provenances("administrative_area", [canonical.id])[str(canonical.id)]["retrieved_at"]
        == alias.capture.fetched_at
    )
    with pytest.raises(IdentityConflict):
        area_run(102, district="another-district")
    assert AdministrativeArea.objects.count() == 1


def test_administrative_repair_and_reversal_keep_source_observations():
    area_run()
    canonical = AdministrativeArea.objects.get()
    with patch(
        "property_platform.modules.evidence.maps.map_import.resolve_administrative_area",
        return_value=None,
    ):
        acquisition = area_run(101)
    duplicate = AdministrativeArea.objects.exclude(pk=canonical.pk).get()
    original_observations = list(MapObservation.objects.values_list("pk", "administrative_area_id"))
    plan = repair_source_identities(run_id=acquisition.id, actor="reviewer")
    assert plan["candidates"] == 1
    repair_source_identities(run_id=acquisition.id, actor="reviewer", apply=True)
    alias = AdministrativeAreaSourceAlias.objects.get()
    duplicate.refresh_from_db()
    assert (
        duplicate.superseded_by_id == canonical.id
        and alias.superseded_revision == duplicate.revision
    )
    assert (
        list(MapObservation.objects.values_list("pk", "administrative_area_id"))
        == original_observations
    )
    assert (
        map_provenances("administrative_area", [canonical.id])[str(canonical.id)]["retrieved_at"]
        == alias.capture.fetched_at
    )
    reverse_identity_decision(
        target="administrative_area",
        decision_id=alias.id,
        actor="reviewer",
        reason="Review",
        apply=True,
    )
    duplicate.refresh_from_db()
    assert duplicate.superseded_by_id is None
    with pytest.raises(IdentityConflict, match="revoked"):
        area_run(101)


def test_administrative_reused_oid_and_changed_shape_do_not_create_duplicate():
    area_run()
    with pytest.raises(IdentityConflict):
        area_run(1, name="A different sector")
    with pytest.raises(IdentityConflict):
        area_run(101, changed_geometry=True)
    assert AdministrativeArea.objects.count() == 1


def test_owner_supersession_rejects_chains():
    canonical, duplicate, _ = legacy_duplicate()
    Parcel.objects.create(
        source_namespace=canonical.source_namespace,
        source_record_id="third",
        superseded_by=duplicate,
        **duplicate_values(canonical),
    )
    with pytest.raises(ValueError, match="Unsafe"):
        with transaction.atomic():
            supersede_parcel(duplicate_id=duplicate.id, canonical_id=canonical.id)


def test_alias_schema_and_database_lifecycle_guards():
    run([plot()])
    run([plot(101)])
    alias = ParcelSourceAlias.objects.get()
    with connection.cursor() as cursor:
        for table in ("parcel_source_alias", "administrative_area_source_alias"):
            cursor.execute(
                "SELECT to_regclass(%s), to_regclass(%s)", ["evidence." + table, "public." + table]
            )
            expected, public = cursor.fetchone()
            assert expected is not None and public is None
    with pytest.raises(IntegrityError), transaction.atomic():
        ParcelSourceAlias.objects.filter(pk=alias.id).update(active=False)
    with pytest.raises(IntegrityError), transaction.atomic():
        ParcelSourceAlias.objects.filter(pk=alias.id).update(canonical_revision=0)
