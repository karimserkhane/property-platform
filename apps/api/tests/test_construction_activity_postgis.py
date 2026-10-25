"""Sentinel-2 ground-change measurements are stored on real PostGIS with their journal."""

import hashlib
import os
from datetime import UTC, datetime

import pytest

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Construction activity requires real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import MultiPolygon, Polygon  # noqa: E402
from django.db import IntegrityError, connection, transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from property_platform.modules.catalog.models import Developer, Parcel, Project  # noqa: E402
from property_platform.modules.evidence import activity_import  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    ConstructionActivityMeasurement,
    IngestionRun,
    ProjectIdentityLink,
    Source,
)
from property_platform.modules.evidence.pipeline_inventory import inventory  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

ACTOR = "integration-test"
BEFORE = "S2C_40RBN_20260629_0_L2A"
AFTER = "S2C_40RBN_20261004_0_L2A"
MEASURED = {
    "method_version": "sentinel-activity-v1",
    "status": "measured",
    "parcel_pixels": 120,
    "clear_pixels": 100,
    "changed_pixels": 40,
    "changed_share": 0.4,
    "median_difference": 0.0412,
    "level": "high",
}


def finished_run(key):
    source, _ = Source.objects.get_or_create(
        key=key, defaults={"name": key, "url": "https://example.com/" + key}
    )
    run = IngestionRun.objects.create(source=source, actor=ACTOR, connector_version="test")
    run.status, run.finished_at = "succeeded", timezone.now()
    run.save(update_fields=["status", "finished_at"])
    return run


def capture(run, url, payload=b"{}"):
    return Capture.objects.create(
        run=run,
        url=url,
        payload=payload,
        byte_length=len(payload),
        content_sha256=hashlib.sha256(payload).hexdigest(),
        http_status=200,
        fetched_at=timezone.now(),
    )


@pytest.fixture
def linked():
    developer = Developer.objects.create(key="aldar", name="Aldar", website_url="https://x.ae/")
    project = Project.objects.create(
        slug="tower",
        name="Tower",
        territory_id="al-reem-island",
        developer=developer,
        website_url="https://x.ae/tower",
    )
    shape = MultiPolygon(Polygon.from_bbox((54.40, 24.49, 54.401, 24.491)), srid=4326)
    parcel = Parcel.objects.create(
        source_namespace="test:parcels",
        source_record_id="1",
        municipality="Abu Dhabi",
        district="Al Reem",
        geometry=shape,
    )
    evidence = capture(finished_run("project:tower"), "https://x.ae/tower")
    return ProjectIdentityLink.objects.create(
        project=project, parcel=parcel, capture=evidence, actor=ACTOR, reason="Reviewed plot"
    )


def windows(run):
    def window(scene_id, acquired_at):
        return {
            "scene": {"scene_id": scene_id, "acquired_at": acquired_at, "tile": "MGRS-40RBN"},
            "capture": capture(run, "https://sentinel-cogs.example/" + scene_id),
        }

    return (
        window(BEFORE, datetime(2026, 6, 29, 6, 50, tzinfo=UTC)),
        window(AFTER, datetime(2026, 10, 4, 6, 50, tzinfo=UTC)),
    )


def test_only_active_links_on_current_parcels_are_measured(linked):
    assert activity_import.measurable_links() == [linked]
    assert activity_import.measurable_links("saadiyat-island") == []
    replacement = Parcel.objects.create(
        source_namespace="test:parcels",
        source_record_id="2",
        municipality="Abu Dhabi",
        district="Al Reem",
        geometry=linked.parcel.geometry,
    )
    linked.parcel.superseded_by = replacement
    linked.parcel.save(update_fields=["superseded_by"])
    assert activity_import.measurable_links() == []


def test_a_measurement_is_stored_once_per_scene_pair_and_journalled(linked):
    run = finished_run("sentinel-activity:al-reem-island")
    before, after = windows(run)
    measurement, created = activity_import.record_measurement(
        run=run, link=linked, before=before, after=after, result=MEASURED
    )
    assert created
    measurement.refresh_from_db()
    assert (measurement.level, str(measurement.changed_share), measurement.tile) == (
        "high",
        "0.4000",
        "MGRS-40RBN",
    )
    again, created = activity_import.record_measurement(
        run=run, link=linked, before=before, after=after, result=MEASURED | {"level": "low"}
    )
    assert (again.pk, again.level, created) == (measurement.pk, "high", False)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM evidence.row_revision "
            "WHERE table_name='construction_activity_measurement'"
        )
        assert cursor.fetchone()[0] == 1
    report = inventory()
    row = next(r for r in report["tables"] if r["table"] == "construction_activity_measurement")
    assert (row["schema"], row["covered"]) == ("evidence", True)


def test_an_unmeasurable_parcel_keeps_no_level(linked):
    run = finished_run("sentinel-activity:al-reem-island")
    before, after = windows(run)
    insufficient = MEASURED | {
        "status": "insufficient_clear_pixels",
        "clear_pixels": 10,
        "changed_pixels": None,
        "changed_share": None,
        "median_difference": None,
        "level": None,
    }
    measurement, _ = activity_import.record_measurement(
        run=run, link=linked, before=before, after=after, result=insufficient
    )
    assert (measurement.level, measurement.changed_share) == ("", None)


def test_the_database_rejects_a_progress_like_or_inverted_measurement(linked):
    run = finished_run("sentinel-activity:al-reem-island")
    before, after = windows(run)
    common = {
        "project": linked.project,
        "parcel": linked.parcel,
        "identity_link": linked,
        "run": run,
        "before_capture": before["capture"],
        "after_capture": after["capture"],
        "tile": "MGRS-40RBN",
        "before_scene_id": BEFORE,
        "after_scene_id": AFTER,
        "before_acquired_at": before["scene"]["acquired_at"],
        "after_acquired_at": after["scene"]["acquired_at"],
        "method_version": "sentinel-activity-v1",
        "status": "measured",
        "parcel_pixels": 120,
        "clear_pixels": 100,
        "changed_pixels": 40,
        "changed_share": "0.4",
        "median_difference": "0.04",
        "level": "high",
    }
    for changes in (
        {"changed_share": "1.5"},
        {"level": "75%"},
        {"after_acquired_at": before["scene"]["acquired_at"]},
        {"status": "insufficient_clear_pixels"},
        {"clear_pixels": 130},
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            ConstructionActivityMeasurement.objects.create(**(common | changes))


def test_window_captures_must_come_from_the_measuring_run(linked):
    run = finished_run("sentinel-activity:al-reem-island")
    before, after = windows(finished_run("other"))
    with pytest.raises(ValueError):
        activity_import.record_measurement(
            run=run, link=linked, before=before, after=after, result=MEASURED
        )
