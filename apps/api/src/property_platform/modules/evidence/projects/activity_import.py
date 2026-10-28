"""Persist Sentinel-2 ground-change measurements of project parcels (B06).

Raster reading and the change index run in ingestion; this module only selects the
parcels to measure and stores a dated, versioned result with its window captures.
A measurement is a signal of ground change, never a progress percentage.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.db import connection, transaction
from django.db.models import Q
from django.db.models.expressions import RawSQL
from django.utils import timezone

from property_platform.modules.catalog.models import Parcel
from property_platform.object_storage.core import MAX_BYTES as OBJECT_MAX_BYTES

from ..activity_models import (
    ACTIVITY_LEVELS,
    ACTIVITY_STATUSES,
    AREA_BASES,
    DERIVED_AREA_M2,
    DERIVING_METHODS,
    ConstructionActivityMeasurement,
)
from ..history.journals import audit_context
from ..media_storage import read_capture
from ..models import Capture, IngestionRun, ProjectIdentityLink, Source
from .project_queries import location_method
from .queries import map_provenances

logger = logging.getLogger(__name__)

SOURCE_KEY = "sentinel-2-l2a-earth-search"
SOURCE_URL = "https://earth-search.aws.element84.com/v1"
LOCK = 8473303
# Each new measurement reads two windows of about 7 MB of byte ranges; twenty parcels
# stay well inside the 512 MiB range session and a 20-minute flow.
MAX_NEW_MEASUREMENTS = 20

RESULT_FIELDS = (
    "method_version",
    "status",
    "parcel_pixels",
    "clear_pixels",
    "changed_pixels",
    "changed_share",
    "median_difference",
    "level",
)
# What a replay must reproduce exactly, besides the project and parcel identities.
RECORD_FIELDS = (
    "area_basis",
    "position_method",
    "parcel_area_m2",
    "tile",
    "before_scene_id",
    "after_scene_id",
    "before_acquired_at",
    "after_acquired_at",
    *RESULT_FIELDS,
)


@dataclass(frozen=True)
class Target:
    """One project parcel to measure, with the reviewed link that justifies it."""

    link: ProjectIdentityLink
    parcel: Parcel
    area_basis: str
    position_method: str
    area_m2: int

    @property
    def project_id(self):
        return self.link.project_id


def _parcels(**filters):
    return Parcel.objects.filter(superseded_by__isnull=True, **filters).annotate(
        area_m2=RawSQL("ST_Area(geometry::geography)", ())
    )


def measurement_targets(territory=None):
    """Project parcels to measure, in the order of the links that justify them.

    A reviewed project-to-parcel link always wins. A project without one is measured
    on the single current parcel containing its reviewed authority point or building
    footprint, when that parcel is between 0.2 and 10 ha (owner decision of 25 October
    2026). Broker, publisher and declared points never stand for a plot.
    """
    links = (
        ProjectIdentityLink.objects.filter(active=True, capture__run__status="succeeded")
        .filter(
            Q(parcel__isnull=False, parcel__superseded_by__isnull=True)
            | Q(place__active=True)
            | Q(building__active=True)
        )
        .select_related("project", "place", "building")
        .order_by("id")
    )
    if territory:
        links = links.filter(project__territory_id=territory)
    links = list(links)
    targets, reviewed = {}, set()
    for link in links:
        if link.parcel_id is not None:
            parcel = _parcels(pk=link.parcel_id).get()
            reviewed.add(link.project_id)
            targets.setdefault(
                (link.project_id, parcel.pk),
                Target(link, parcel, "reviewed_parcel", "cadastral_parcel", round(parcel.area_m2)),
            )
    points = map_provenances(
        "place", [link.place_id for link in links if link.place_id], include_method=True
    )
    for link in links:
        if link.parcel_id is not None or link.project_id in reviewed:
            continue
        if link.place_id is not None:
            method = location_method("place", points.get(str(link.place_id), {}).get("_method"))
            position = link.place.geometry
        else:
            method, position = "building_footprint", link.building.geometry.point_on_surface
        if method not in DERIVING_METHODS:
            continue
        # A position on a shared boundary, or outside every parcel, has no single plot.
        found = list(_parcels(geometry__intersects=position)[:2])
        if len(found) != 1:
            continue
        parcel, area = found[0], round(found[0].area_m2)
        if not DERIVED_AREA_M2[0] <= area <= DERIVED_AREA_M2[1]:
            continue
        targets.setdefault(
            (link.project_id, parcel.pk),
            Target(link, parcel, "parcel_containing_position", method, area),
        )
    return sorted(targets.values(), key=lambda target: (target.link.id, str(target.parcel.pk)))


def _scene(window):
    scene = window["scene"]
    return scene["scene_id"], scene["acquired_at"], scene["tile"], window["capture"]


def record_measurement(*, run, target, before, after, result):
    """Store one comparison; an identical pair and method version is kept, not redone.

    ``before`` and ``after`` hold the selected ``scene`` record and the window
    ``capture`` of each date; ``result`` is the ingestion change signal.
    """
    if not target.link.active or target.area_basis not in AREA_BASES:
        raise ValueError("A measurement needs an active reviewed link and a known area")
    if set(result) != set(RESULT_FIELDS):
        raise ValueError("Unexpected measurement fields")
    if result["status"] not in ACTIVITY_STATUSES or (
        result["level"] is not None and result["level"] not in ACTIVITY_LEVELS
    ):
        raise ValueError("Unexpected measurement result")
    before_id, before_at, before_tile, before_capture = _scene(before)
    after_id, after_at, after_tile, after_capture = _scene(after)
    if before_tile != after_tile:
        raise ValueError("Both scenes must come from one MGRS tile")
    if before_capture.run_id != run.pk or after_capture.run_id != run.pk:
        raise ValueError("Window captures must belong to the measuring run")
    values = {
        **{key: result[key] for key in RESULT_FIELDS if key not in {"level", "method_version"}},
        "level": result["level"] or "",
        "changed_share": _decimal(result["changed_share"]),
        "median_difference": _decimal(result["median_difference"]),
    }
    with transaction.atomic():
        measurement, created = ConstructionActivityMeasurement.objects.get_or_create(
            project_id=target.project_id,
            parcel_id=target.parcel.pk,
            before_scene_id=before_id,
            after_scene_id=after_id,
            method_version=result["method_version"],
            defaults={
                "identity_link": target.link,
                "area_basis": target.area_basis,
                "position_method": target.position_method,
                "parcel_area_m2": target.area_m2,
                "run": run,
                "before_capture": before_capture,
                "after_capture": after_capture,
                "tile": before_tile,
                "before_acquired_at": before_at,
                "after_acquired_at": after_at,
                **values,
            },
        )
    return measurement, created


def _decimal(value):
    return None if value is None else Decimal(str(value))


def measure_activity(*, actor, run_key, collector, territory=None, limit=MAX_NEW_MEASUREMENTS):
    """Measure the latest scene pair of each measurable parcel; resume where budgets stop.

    ``collector`` supplies ``method_version``, ``scenes(bbox)``, ``window(scene,
    geometry)`` (None when the parcel cannot be read on that scene) and ``signal(before,
    after, geometry)`` computed from capture bytes. The API never reads rasters.
    """
    source, _ = Source.objects.get_or_create(
        key=SOURCE_KEY,
        defaults={"name": "Copernicus Sentinel-2 L2A (Earth Search)", "url": SOURCE_URL},
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [LOCK])
        if not cursor.fetchone()[0]:
            return {"status": "succeeded", "summary": {"busy": True}}
    try:
        with audit_context(actor=actor):
            run = IngestionRun.objects.create(source=source, actor=actor, connector_version=run_key)
            summary = {
                "targets": 0,
                "derived": 0,
                "pairs": 0,
                "measured": 0,
                "existing": 0,
                "unreadable": 0,
                "failed": 0,
                "deferred": 0,
            }
            try:
                _measure(run, collector, measurement_targets(territory), summary, limit)
                run.status = "quarantined" if summary["failed"] else "succeeded"
            except Exception as exc:
                logger.error("Construction activity run %s failed", run.pk, exc_info=exc)
                run.status, run.error = "failed", type(exc).__name__
            run.summary = summary
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "error", "summary", "finished_at"])
            return {"status": run.status, "summary": summary, "error": run.error}
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK])


def _measure(run, collector, targets, summary, limit):
    summary["targets"] = len(targets)
    summary["derived"] = sum(target.area_basis != "reviewed_parcel" for target in targets)
    if not targets:
        return
    extents = [target.parcel.geometry.extent for target in targets]
    bbox = (
        min(row[0] for row in extents),
        min(row[1] for row in extents),
        max(row[2] for row in extents),
        max(row[3] for row in extents),
    )
    found = collector.scenes(bbox)
    # Every search page is kept, so each selected scene cites the page that listed it.
    pages = [_capture(run, page["payload"], page["receipt"]) for page in found["pages"]]
    tiles = {}
    for scene in found["scenes"]:
        tiles.setdefault(scene["tile"], []).append(scene)
    # The newest pair first: a parcel in the overlap of two tiles is measured once.
    pairs = sorted(
        ((scenes[-2], scenes[-1]) for scenes in tiles.values() if len(scenes) >= 2),
        key=lambda pair: (pair[1]["acquired_at"], pair[1]["tile"]),
        reverse=True,
    )
    summary["pairs"] = len(pairs)
    windows = {}
    for target in targets:
        geometry = json.loads(target.parcel.geometry.geojson)
        outcome = "unreadable"
        try:
            for before, after in pairs:
                if ConstructionActivityMeasurement.objects.filter(
                    project_id=target.project_id,
                    parcel_id=target.parcel.pk,
                    before_scene_id=before["scene_id"],
                    after_scene_id=after["scene_id"],
                    method_version=collector.method_version,
                ).exists():
                    outcome = "existing"
                    break
                if summary["measured"] >= limit:
                    outcome = "deferred"
                    break
                captured = []
                for scene in (before, after):
                    key = (scene["scene_id"], target.parcel.pk)
                    if key not in windows:
                        window = collector.window(scene, geometry)
                        windows[key] = window and _capture(
                            run, window["payload"], window["receipt"], pages[scene["page"]]
                        )
                    if windows[key] is None:
                        break
                    captured.append(windows[key])
                if len(captured) < 2:
                    continue
                result = collector.signal(_body(captured[0]), _body(captured[1]), geometry)
                record_measurement(
                    run=run,
                    target=target,
                    before={"scene": before, "capture": captured[0]},
                    after={"scene": after, "capture": captured[1]},
                    result=result,
                )
                outcome = "measured"
                break
        except Exception as exc:
            logger.warning("Activity of parcel %s was not measured", target.parcel.pk, exc_info=exc)
            outcome = "failed"
        summary[outcome] += 1


def _body(capture):
    """Window bytes from SQL or from their verified archived copy."""
    return read_capture(capture, max_bytes=OBJECT_MAX_BYTES)


def _capture(run, payload, receipt, parent=None):
    return Capture.objects.create(
        run=run,
        parent_capture=parent,
        payload=payload,
        byte_length=len(payload),
        content_sha256=hashlib.sha256(payload).hexdigest(),
        **receipt,
    )


def measurement_record(measurement):
    """Comparable values of one stored measurement, keyed by source identities, not UUIDs."""
    values = {}
    for field in RECORD_FIELDS:
        value = getattr(measurement, field)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = str(value)
        values[field] = value
    return {
        "project": measurement.project.slug,
        "parcel": [measurement.parcel.source_namespace, measurement.parcel.source_record_id],
        "values": values,
    }


def export_run(run, archive_capture):
    """Rebuild-check step of one measuring run: its captures and the measurements to redo.

    ``archive_capture`` stores the verified bytes of a capture and returns its manifest
    item; each item names the index of its parent capture (the search page of a window).
    """
    captures = list(Capture.objects.filter(run=run).order_by("ingested_at", "pk"))
    # Search pages before the windows that cite them, whatever the clock resolution.
    captures.sort(key=lambda capture: capture.parent_capture_id is not None)
    index = {capture.pk: position for position, capture in enumerate(captures)}
    items = [
        {**archive_capture(capture), "parent": index.get(capture.parent_capture_id)}
        for capture in captures
    ]
    measurements = [
        {
            **measurement_record(measurement),
            "before_capture": index[measurement.before_capture_id],
            "after_capture": index[measurement.after_capture_id],
        }
        for measurement in ConstructionActivityMeasurement.objects.filter(run=run)
        .select_related("project", "parcel")
        .order_by("created_at", "pk")
    ]
    return {
        "operation": "construction_activity",
        "scope": "all",
        "run": str(run.pk),
        "original_version": run.connector_version,
        "captures": items,
        "measurements": measurements,
    }


def replay_run(step, *, load, actor, run_key, signal):
    """Measure again, from archived window bytes only, what one original run measured.

    The parcel must still be a measurement target of the rebuilt catalogue for the same
    reason, and ``signal`` (the ingestion change signal) must give the same result.
    Returns the measurements that differ; nothing is copied from the original values.
    """
    source, _ = Source.objects.get_or_create(
        key=SOURCE_KEY,
        defaults={"name": "Copernicus Sentinel-2 L2A (Earth Search)", "url": SOURCE_URL},
    )
    run = IngestionRun.objects.create(source=source, actor=actor, connector_version=run_key)
    captures = []
    for position, item in enumerate(step["captures"]):
        parent = item.get("parent")
        if parent is not None and not 0 <= parent < position:
            raise ValueError("An archived capture must follow its parent")
        payload, receipt = load(item)
        captures.append(
            _capture(run, payload, receipt, None if parent is None else captures[parent])
        )
    targets = {}
    for target in measurement_targets():
        key = target.parcel.source_namespace, target.parcel.source_record_id
        targets[(target.link.project.slug, *key)] = target
    differences = []
    for expected in step["measurements"]:
        values = expected["values"]
        identity = {"project": expected["project"], "parcel": expected["parcel"]}
        target = targets.get((expected["project"], *expected["parcel"]))
        if target is None:
            differences.append({**identity, "reason": "not_a_measurement_target"})
            continue
        before, after = captures[expected["before_capture"]], captures[expected["after_capture"]]
        result = signal(_body(before), _body(after), json.loads(target.parcel.geometry.geojson))
        measurement, _ = record_measurement(
            run=run,
            target=target,
            before={"scene": _archived_scene(values, "before"), "capture": before},
            after={"scene": _archived_scene(values, "after"), "capture": after},
            result=result,
        )
        # Compare what the database keeps (rounded decimals), not the Python values.
        measurement.refresh_from_db()
        actual = measurement_record(measurement)["values"]
        if actual != values:
            differences.append({**identity, "expected": values, "actual": actual})
    run.status = "failed" if differences else "succeeded"
    run.summary = {"replayed": len(step["measurements"]), "differences": len(differences)}
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "summary", "finished_at"])
    return differences


def _archived_scene(values, side):
    return {
        "scene_id": values[f"{side}_scene_id"],
        "acquired_at": datetime.fromisoformat(values[f"{side}_acquired_at"]),
        "tile": values["tile"],
    }
