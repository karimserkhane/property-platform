"""Sentinel-2 ground-change measurements are stored on real PostGIS with their journal."""

import hashlib
import os
from datetime import UTC, datetime

import pytest

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Construction activity requires real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import MultiPolygon, Point, Polygon  # noqa: E402
from django.db import IntegrityError, connection, transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from property_platform.modules.catalog.models import (  # noqa: E402
    Developer,
    Parcel,
    Place,
    Project,
)
from property_platform.modules.evidence.history.pipeline_inventory import inventory  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    ConstructionActivityMeasurement,
    IngestionRun,
    MapObservation,
    ProjectIdentityLink,
    Source,
)
from property_platform.modules.evidence.projects import activity_import  # noqa: E402

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


def reviewed(link):
    return activity_import.Target(link, link.parcel, "reviewed_parcel", "cadastral_parcel", 11_000)


def test_reviewed_parcel_links_on_current_parcels_are_measured(linked):
    [target] = activity_import.measurement_targets()
    assert (target.link, target.parcel, target.area_basis, target.position_method) == (
        linked,
        linked.parcel,
        "reviewed_parcel",
        "cadastral_parcel",
    )
    assert 10_000 < target.area_m2 < 12_000
    assert activity_import.measurement_targets("saadiyat-island") == []
    replacement = Parcel.objects.create(
        source_namespace="test:parcels",
        source_record_id="2",
        municipality="Abu Dhabi",
        district="Al Reem",
        geometry=linked.parcel.geometry,
    )
    linked.parcel.superseded_by = replacement
    linked.parcel.save(update_fields=["superseded_by"])
    assert activity_import.measurement_targets() == []


def located(slug, point, method):
    """A project placed by a reviewed link on a source point observed with a given method."""
    project = Project.objects.create(
        slug=slug,
        name=slug,
        territory_id="al-reem-island",
        developer=Developer.objects.get_or_create(
            key="aldar", defaults={"name": "Aldar", "website_url": "https://x.ae/"}
        )[0],
        website_url="https://x.ae/" + slug,
    )
    place = Place.objects.create(
        source_namespace="test:points", source_record_id=slug, geometry=Point(*point, srid=4326)
    )
    run = finished_run("points:" + slug)
    MapObservation.objects.create(
        place=place,
        capture=capture(run, "https://x.ae/register/" + slug),
        source_record_id=slug,
        source_url="https://x.ae/register/" + slug,
        raw_attributes={"method": method},
        record_sha256="0" * 64,
        mapping_version="test",
        action="created",
        target_revision=1,
    )
    return ProjectIdentityLink.objects.create(
        project=project,
        place=place,
        capture=capture(finished_run("project:" + slug), "https://x.ae/" + slug),
        actor=ACTOR,
        reason="Reviewed project point",
    )


def plot(record, box):
    return Parcel.objects.create(
        source_namespace="test:parcels",
        source_record_id=record,
        municipality="Abu Dhabi",
        district="Al Reem",
        geometry=MultiPolygon(Polygon.from_bbox(box), srid=4326),
    )


def test_a_reliable_point_stands_for_the_single_parcel_that_contains_it(linked):
    registered = "authority_registered_project_coordinates"
    authority = located("registered", (54.4005, 24.4905), registered)
    located("brokered", (54.4005, 24.4905), "broker_project_coordinates")
    # On a shared boundary, two parcels contain the point: none is chosen.
    plot("west", (54.41, 24.49, 54.411, 24.491))
    plot("east", (54.411, 24.49, 54.412, 24.491))
    located("boundary", (54.411, 24.4905), registered)
    # A master plan of about 1 km a side is larger than one building site.
    plot("master", (54.42, 24.49, 54.43, 24.50))
    located("master", (54.425, 24.495), registered)
    targets = activity_import.measurement_targets()
    assert [(t.link.project.slug, t.area_basis, t.position_method) for t in targets] == [
        ("tower", "reviewed_parcel", "cadastral_parcel"),
        ("registered", "parcel_containing_position", "authority_point"),
    ]
    assert targets[1].link == authority and targets[1].parcel == linked.parcel
    # A project with a reviewed parcel is never measured on a derived one as well.
    ProjectIdentityLink.objects.create(
        project=linked.project,
        place=Place.objects.create(
            source_namespace="test:points",
            source_record_id="tower",
            geometry=Point(54.425, 24.495, srid=4326),
        ),
        capture=linked.capture,
        actor=ACTOR,
        reason="Reviewed project point",
    )
    assert len(activity_import.measurement_targets()) == 2


def test_a_measurement_is_stored_once_per_scene_pair_and_journalled(linked):
    run = finished_run("sentinel-activity:al-reem-island")
    before, after = windows(run)
    measurement, created = activity_import.record_measurement(
        run=run, target=reviewed(linked), before=before, after=after, result=MEASURED
    )
    assert created
    measurement.refresh_from_db()
    assert (measurement.level, str(measurement.changed_share), measurement.tile) == (
        "high",
        "0.4000",
        "MGRS-40RBN",
    )
    again, created = activity_import.record_measurement(
        run=run,
        target=reviewed(linked),
        before=before,
        after=after,
        result=MEASURED | {"level": "low"},
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
        run=run, target=reviewed(linked), before=before, after=after, result=insufficient
    )
    assert (measurement.level, measurement.changed_share) == ("", None)


def test_the_database_rejects_a_progress_like_or_inverted_measurement(linked):
    run = finished_run("sentinel-activity:al-reem-island")
    before, after = windows(run)
    common = {
        "project": linked.project,
        "parcel": linked.parcel,
        "identity_link": linked,
        "area_basis": "reviewed_parcel",
        "position_method": "cadastral_parcel",
        "parcel_area_m2": 11_000,
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
        {"position_method": "authority_point"},
        {"area_basis": "parcel_containing_position", "position_method": "broker_point"},
        {
            "area_basis": "parcel_containing_position",
            "position_method": "authority_point",
            "parcel_area_m2": 1_500,
        },
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            ConstructionActivityMeasurement.objects.create(**(common | changes))


def test_window_captures_must_come_from_the_measuring_run(linked):
    run = finished_run("sentinel-activity:al-reem-island")
    before, after = windows(finished_run("other"))
    with pytest.raises(ValueError):
        activity_import.record_measurement(
            run=run, target=reviewed(linked), before=before, after=after, result=MEASURED
        )


class FakeCollector:
    """Stands in for the ingestion collector: two pages, one tile, one window per scene."""

    method_version = "sentinel-activity-v1"

    def __init__(self, *, readable=True, failing=False):
        self.readable, self.failing, self.windows = readable, failing, []

    def scenes(self, bbox):
        assert bbox[0] < bbox[2] and bbox[1] < bbox[3]
        receipt = {
            "url": "https://earth-search.aws.element84.com/v1/search?collections=x",
            "fetched_started_at": timezone.now(),
            "fetched_at": timezone.now(),
            "http_status": 200,
            "acquisition_method": "scheduled_https_collect",
        }
        scenes = [
            {"scene_id": BEFORE, "acquired_at": datetime(2026, 6, 29, tzinfo=UTC), "page": 0},
            {"scene_id": AFTER, "acquired_at": datetime(2026, 10, 4, tzinfo=UTC), "page": 1},
        ]
        return {
            "pages": [{"payload": b'{"page":1}', "receipt": receipt}] * 2,
            "scenes": [scene | {"tile": "MGRS-40RBN"} for scene in scenes],
        }

    def window(self, scene, geometry):
        if self.failing:
            raise ValueError("Source transport failed")
        self.windows.append(scene["scene_id"])
        if not self.readable:
            return None
        return {
            "payload": scene["scene_id"].encode(),
            "receipt": {
                "url": "https://earth-search.aws.element84.com/v1/items/" + scene["scene_id"],
                "fetched_started_at": timezone.now(),
                "fetched_at": timezone.now(),
                "http_status": 206,
                "acquisition_method": "sentinel_cog_window_ranges",
            },
        }

    def signal(self, before, after, geometry):
        assert (before, after) == (BEFORE.encode(), AFTER.encode())
        assert geometry["type"] == "MultiPolygon"
        return MEASURED


def test_a_run_measures_the_latest_pair_from_captured_windows_once(linked):
    collector = FakeCollector()
    result = activity_import.measure_activity(actor=ACTOR, run_key="t:1", collector=collector)
    assert result["status"] == "succeeded"
    assert (result["summary"]["measured"], result["summary"]["pairs"]) == (1, 1)
    measurement = ConstructionActivityMeasurement.objects.get()
    assert measurement.before_capture.parent_capture.run_id == measurement.run_id
    assert bytes(measurement.after_capture.payload) == AFTER.encode()
    assert measurement.after_capture.http_status == 206
    again = activity_import.measure_activity(actor=ACTOR, run_key="t:2", collector=collector)
    assert (again["summary"]["existing"], again["summary"]["measured"]) == (1, 0)
    assert collector.windows == [BEFORE, AFTER]


def test_unreadable_windows_and_budgets_leave_no_measurement(linked):
    unreadable = activity_import.measure_activity(
        actor=ACTOR, run_key="t:1", collector=FakeCollector(readable=False)
    )
    assert (unreadable["status"], unreadable["summary"]["unreadable"]) == ("succeeded", 1)
    deferred = activity_import.measure_activity(
        actor=ACTOR, run_key="t:2", collector=FakeCollector(), limit=0
    )
    assert deferred["summary"]["deferred"] == 1
    failed = activity_import.measure_activity(
        actor=ACTOR, run_key="t:3", collector=FakeCollector(failing=True)
    )
    assert (failed["status"], failed["summary"]["failed"]) == ("quarantined", 1)
    assert not ConstructionActivityMeasurement.objects.exists()
    runs = IngestionRun.objects.filter(source__key=activity_import.SOURCE_KEY)
    statuses = sorted(runs.values_list("status", flat=True))
    assert statuses == ["quarantined", "succeeded", "succeeded"]


def test_a_run_without_measurable_parcels_reads_nothing(db):
    result = activity_import.measure_activity(
        actor=ACTOR, run_key="t:1", collector=FakeCollector(failing=True)
    )
    assert (result["status"], result["summary"]["targets"]) == ("succeeded", 0)


def _forget_measuring_runs():
    """Leave the catalogue and its links, as a rebuilt database has them before B06.

    Original captures cannot be deleted; the replay writes its own run and captures.
    """
    ConstructionActivityMeasurement.objects.all().delete()


def _replayed(tmp_path, signal):
    from uuid import uuid4

    from property_platform.modules.evidence.rebuild import rebuild_archive as archive

    activity_import.measure_activity(actor=ACTOR, run_key="t:1", collector=FakeCollector())
    archive.export_archive(tmp_path)
    manifest = archive.json.loads((tmp_path / "manifest.json").read_text("utf-8"))
    step = next(s for s in manifest["steps"] if s["operation"] == "construction_activity")
    _forget_measuring_runs()
    archive.replay_archive(tmp_path, "integration-rebuild", str(uuid4()), activity_signal=signal)
    return step, archive.json.loads((tmp_path / "report.json").read_text("utf-8"))


def test_rebuild_check_measures_again_from_archived_windows_only(linked, tmp_path):
    seen = []

    def signal(before, after, geometry):
        seen.append((before, after))
        return FakeCollector().signal(before, after, geometry)

    step, report = _replayed(tmp_path, signal)
    assert step["measurements"][0]["project"] == "tower"
    assert step["measurements"][0]["parcel"] == ["test:parcels", "1"]
    assert [item["parent"] for item in step["captures"]] == [None, None, 0, 1]
    assert seen == [(BEFORE.encode(), AFTER.encode())]
    outcome = next(s for s in report["steps"] if s["operation"] == "construction_activity")
    assert outcome["status"] == "succeeded", outcome
    table = next(
        t for t in report["tables"] if t["table"] == "evidence.construction_activity_measurement"
    )
    assert (table["expected"], table["actual"], table["matches"]) == (1, 1, True)
    measurement = ConstructionActivityMeasurement.objects.get()
    assert measurement.before_capture.parent_capture.run_id == measurement.run_id
    assert measurement.run.actor == "integration-rebuild"


def test_a_different_replayed_signal_fails_the_rebuild_check(linked, tmp_path):
    step, report = _replayed(tmp_path, lambda *args: MEASURED | {"changed_pixels": 41})
    outcome = next(s for s in report["steps"] if s["operation"] == "construction_activity")
    assert outcome["status"] == "failed"
    (difference,) = outcome["measurements"]
    assert (difference["expected"]["changed_pixels"], difference["actual"]["changed_pixels"]) == (
        40,
        41,
    )
    assert report["ok"] is False


def test_activity_replay_without_the_ingestion_signal_fails(linked, tmp_path):
    from uuid import uuid4

    from property_platform.modules.evidence.rebuild import rebuild_archive as archive

    activity_import.measure_activity(actor=ACTOR, run_key="t:1", collector=FakeCollector())
    archive.export_archive(tmp_path)
    _forget_measuring_runs()
    result = archive.replay_archive(tmp_path, "integration-rebuild", str(uuid4()))
    assert result["failed_steps"] == 1
    assert not ConstructionActivityMeasurement.objects.exists()
