"""Satellite ground-change signal of a project's parcels, for its sheet (B07).

Read-only over the measurements of B06, in one query. Each measured parcel shows its
latest stored comparison of two Sentinel-2 scenes. A level describes ground change
between two dates; it is never a construction progress percentage, so the changed
share is not exposed.
"""

from ..activity_models import ConstructionActivityMeasurement
from .activity_import import SOURCE_URL
from .project_queries import _withdrawn

SOURCE_NAME = "Copernicus Sentinel-2 L2A"


def _window(capture):
    return {"url": capture.url, "content_sha256": capture.content_sha256}


def _parcel(row):
    return {
        "source_namespace": row.parcel.source_namespace,
        "source_record_id": row.parcel.source_record_id,
        "official_plot_id": row.parcel.official_plot_id or None,
        # Values as they were when the parcel was measured.
        "area_m2": row.parcel_area_m2,
        "area_basis": row.area_basis,
        "position_method": row.position_method,
        "latest": {
            "status": row.status,
            "level": row.level or None,
            "method_version": row.method_version,
            "tile": row.tile,
            "before_scene_id": row.before_scene_id,
            "after_scene_id": row.after_scene_id,
            "before_acquired_at": row.before_acquired_at,
            "after_acquired_at": row.after_acquired_at,
            "parcel_pixels": row.parcel_pixels,
            "clear_pixels": row.clear_pixels,
            "measured_at": row.created_at,
            "before_window": _window(row.before_capture),
            "after_window": _window(row.after_capture),
        },
    }


def project_activity(project):
    """Latest measurement of each parcel, while the reviewed link behind it is active."""
    latest = {}
    rows = (
        ConstructionActivityMeasurement.objects.filter(project=project, identity_link__active=True)
        .exclude(_withdrawn("identity_link__capture__url"))
        .select_related("parcel", "before_capture", "after_capture")
        .defer("parcel__geometry", "before_capture__payload", "after_capture__payload")
        .order_by("-after_acquired_at", "-before_acquired_at", "-created_at", "-id")
    )
    for row in rows:
        latest.setdefault(row.parcel_id, row)
    return {
        "source": {"name": SOURCE_NAME, "url": SOURCE_URL},
        "parcels": sorted(
            (_parcel(row) for row in latest.values()),
            key=lambda item: (item["source_namespace"], item["source_record_id"]),
        ),
    }
