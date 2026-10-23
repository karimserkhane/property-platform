"""Typed snapshots of public context; never merge an amenity into property identity."""

import hashlib
import json

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Point
from django.db import transaction
from django.utils import timezone

from . import abu_dhabi
from .models import (
    BusRouteObservation,
    Capture,
    CensusMeasureObservation,
    DistrictBoundaryObservation,
    HealthFacilityObservation,
    IngestionRun,
    PublicContextSnapshot,
    SchoolObservation,
    Source,
)
from .runs import mark_failed

MODELS = {
    "districts": DistrictBoundaryObservation,
    "health": HealthFacilityObservation,
    "schools": SchoolObservation,
    "mobility": BusRouteObservation,
    "statistics": CensusMeasureObservation,
}


def import_context(*, scope, actor, acquisition):
    feed = abu_dhabi.feed_for(scope)
    source, _ = Source.objects.get_or_create(
        key=feed.key, defaults={"name": feed.name, "url": feed.page_url}
    )
    run = IngestionRun.objects.create(
        source=source, actor=actor, connector_version=abu_dhabi.VERSION
    )
    try:

        def acquire(url, params):
            abu_dhabi.validate_request(scope, url, params)
            payload, receipt = acquisition(url, params)
            if receipt["url"] != url:
                raise abu_dhabi.ContextError("Mismatched context receipt URL")
            capture = Capture.objects.create(
                run=run,
                payload=payload,
                byte_length=len(payload),
                content_sha256=hashlib.sha256(payload).hexdigest(),
                **receipt,
            )
            if receipt["http_status"] != 200:
                raise abu_dhabi.ContextError("Public context source unavailable")
            return payload, capture

        capture, rows, modified = abu_dhabi.collect(scope, acquire)
        dataset = scope.split(":")[1]
        previous = (
            PublicContextSnapshot.objects.filter(dataset=dataset, territory="abu-dhabi")
            .order_by("-capture__fetched_at", "-created_at")
            .first()
        )
        if previous and len(rows) < previous.source_row_count * 0.8:
            raise abu_dhabi.ContextError(
                "Unexpected loss of context coverage; source review required"
            )
        with transaction.atomic():
            snapshot = PublicContextSnapshot.objects.create(
                run=run,
                capture=capture,
                dataset=dataset,
                territory="abu-dhabi",
                source_row_count=len(rows),
                source_modified_date=modified,
                reuse_status=feed.reuse_status,
            )
            observations = []
            for path, raw, values in rows:
                values = dict(values)
                if dataset in {"health", "schools"}:
                    values["location"] = Point(
                        values.pop("longitude"), values.pop("latitude"), srid=4326
                    )
                elif dataset == "districts":
                    shape = GEOSGeometry(json.dumps(values.pop("geometry")), srid=4326)
                    if not shape.valid or shape.empty:
                        raise abu_dhabi.ContextError("Invalid district topology")
                    values["geometry"] = (
                        MultiPolygon(shape, srid=4326) if shape.geom_type == "Polygon" else shape
                    )
                observations.append(
                    MODELS[dataset](
                        snapshot=snapshot,
                        field_path=path,
                        record_sha256=abu_dhabi.digest(raw),
                        **values,
                    )
                )
            MODELS[dataset].objects.bulk_create(observations, batch_size=500)
        run.status = "succeeded"
        run.summary = {
            "dataset": dataset,
            "observations": len(rows),
            "snapshot_id": str(snapshot.pk),
            "reuse_status": feed.reuse_status,
        }
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "summary", "finished_at"])
        return run
    except Exception as exc:
        mark_failed(run, exc)
        raise
