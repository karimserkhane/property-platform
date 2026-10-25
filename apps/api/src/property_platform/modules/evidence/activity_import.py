"""Persist Sentinel-2 ground-change measurements of reviewed project parcels (B06).

Raster reading and the change index run in ingestion; this module only selects the
parcels to measure and stores a dated, versioned result with its window captures.
A measurement is a signal of ground change, never a progress percentage.
"""

from decimal import Decimal

from django.db import transaction

from .activity_models import ACTIVITY_LEVELS, ACTIVITY_STATUSES, ConstructionActivityMeasurement
from .models import ProjectIdentityLink

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
