"""Persist Sentinel-2 ground-change measurements of reviewed project parcels (B06).

Raster reading and the change index run in ingestion; this module only selects the
parcels to measure and stores a dated, versioned result with its window captures.
A measurement is a signal of ground change, never a progress percentage.
"""

import hashlib
import json
import logging
from decimal import Decimal

from django.db import connection, transaction
from django.utils import timezone

from .activity_models import ACTIVITY_LEVELS, ACTIVITY_STATUSES, ConstructionActivityMeasurement
from .history import audit_context
from .models import Capture, IngestionRun, ProjectIdentityLink, Source

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


def measurable_links(territory=None):
    """Active, reviewed project-to-parcel links on current parcels, oldest first.

    Only a cadastral parcel gives the boundary a measurement needs; a declared point
    or a building footprint never stands in for it.
    """
    links = ProjectIdentityLink.objects.filter(
        active=True,
        parcel__isnull=False,
        parcel__superseded_by__isnull=True,
        capture__run__status="succeeded",
    ).select_related("project", "parcel")
    if territory:
        links = links.filter(project__territory_id=territory)
    return list(links.order_by("id"))


def _scene(window):
    scene = window["scene"]
    return scene["scene_id"], scene["acquired_at"], scene["tile"], window["capture"]


def record_measurement(*, run, link, before, after, result):
    """Store one comparison; an identical pair and method version is kept, not redone.

    ``before`` and ``after`` hold the selected ``scene`` record and the window
    ``capture`` of each date; ``result`` is the ingestion change signal.
    """
    if not link.active or link.parcel_id is None:
        raise ValueError("A measurement needs an active parcel link")
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
            parcel_id=link.parcel_id,
            before_scene_id=before_id,
            after_scene_id=after_id,
            method_version=result["method_version"],
            defaults={
                "project_id": link.project_id,
                "identity_link": link,
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
                "links": 0,
                "pairs": 0,
                "measured": 0,
                "existing": 0,
                "unreadable": 0,
                "failed": 0,
                "deferred": 0,
            }
            try:
                _measure(run, collector, measurable_links(territory), summary, limit)
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


def _measure(run, collector, links, summary, limit):
    summary["links"] = len(links)
    if not links:
        return
    extents = [link.parcel.geometry.extent for link in links]
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
    for link in links:
        geometry = json.loads(link.parcel.geometry.geojson)
        outcome = "unreadable"
        try:
            for before, after in pairs:
                if ConstructionActivityMeasurement.objects.filter(
                    parcel_id=link.parcel_id,
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
                    key = (scene["scene_id"], link.parcel_id)
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
                result = collector.signal(
                    bytes(captured[0].payload), bytes(captured[1].payload), geometry
                )
                record_measurement(
                    run=run,
                    link=link,
                    before={"scene": before, "capture": captured[0]},
                    after={"scene": after, "capture": captured[1]},
                    result=result,
                )
                outcome = "measured"
                break
        except Exception as exc:
            logger.warning("Activity of parcel %s was not measured", link.parcel_id, exc_info=exc)
            outcome = "failed"
        summary[outcome] += 1


def _capture(run, payload, receipt, parent=None):
    return Capture.objects.create(
        run=run,
        parent_capture=parent,
        payload=payload,
        byte_length=len(payload),
        content_sha256=hashlib.sha256(payload).hexdigest(),
        **receipt,
    )
