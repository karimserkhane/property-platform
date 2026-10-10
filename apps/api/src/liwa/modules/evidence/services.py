import hashlib
import json
import time

from django.db import connection, transaction
from django.utils import timezone

from liwa.modules.catalog.services import geometry_from_rings, reconcile_parcel

from . import onwani
from .models import (
    AuditEvent,
    Capture,
    IngestionRun,
    ParcelObservation,
    QuarantinedObservation,
    Source,
)

# Session lock serializes this connector across commands/workers on this database.
LOCK_KEY = 716548219


def import_onwani(*, actor):
    if connection.vendor != "postgresql":
        raise ValueError("Onwani import requires PostgreSQL/PostGIS")
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [LOCK_KEY])
        if not cursor.fetchone()[0]:
            raise ValueError("An Onwani import is already running")
    run = None
    try:
        source, _ = Source.objects.get_or_create(
            key=onwani.SOURCE_KEY,
            defaults={"name": "DMT / Onwani PLOT — Al Reem Island", "url": onwani.BASE_URL},
        )
        run = IngestionRun.objects.create(
            source=source, connector_version=onwani.VERSION, actor=actor
        )

        def acquire(params=None):
            payload, receipt = onwani.fetch(params)
            # Preserve the exact bounded response before parsing or validating its contents.
            capture = Capture.objects.create(
                run=run,
                payload=payload,
                byte_length=len(payload),
                content_sha256=hashlib.sha256(payload).hexdigest(),
                **receipt,
            )
            if receipt["http_status"] != 200:
                raise onwani.SourceError("Source returned a non-success HTTP status")
            return onwani.decode(payload), capture

        metadata, _ = acquire()
        onwani.validate_metadata(metadata)
        listing, _ = acquire({"where": onwani.WHERE, "returnIdsOnly": "true"})
        ids = onwani.object_ids(listing)
        staged = []
        quarantined = []
        seen = set()
        for offset in range(0, len(ids), 100):
            if offset:
                time.sleep(0.25)
            batch_ids = ids[offset : offset + 100]
            batch, capture = acquire(
                {
                    "where": onwani.WHERE,
                    "objectIds": ",".join(map(str, batch_ids)),
                    "outFields": onwani.FIELDS,
                    "returnGeometry": "true",
                    "outSR": "4326",
                }
            )
            if batch.get("spatialReference", {}).get("wkid") != 4326:
                raise onwani.SourceError("Unexpected response CRS")
            features = batch.get("features")
            if not isinstance(features, list):
                raise onwani.SourceError("Missing feature list")
            for index, feature in enumerate(features):
                record = onwani.parse_feature(feature)
                oid = int(record["record_id"])
                if oid not in batch_ids or oid in seen:
                    raise onwani.SourceError("Unexpected or duplicate batch identity")
                seen.add(oid)
                try:
                    geometry = geometry_from_rings(record["rings"])
                except ValueError:
                    quarantined.append((record, capture, index))
                    continue
                digest = hashlib.sha256(
                    json.dumps(feature, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                staged.append((record, geometry, capture, index, digest))
            if set(batch_ids) - seen:
                raise onwani.SourceError("Incomplete batch")
        latest, _ = acquire({"where": onwani.WHERE, "returnIdsOnly": "true"})
        if set(onwani.object_ids(latest)) != seen or seen != set(ids):
            raise onwani.SourceError("Territory coverage changed during collection")
        summary = {
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "observed": len(seen),
            "quarantined": len(quarantined),
        }
        # No catalogue writes before a complete valid acquisition; atomic application and audit.
        with transaction.atomic():
            for record, capture, index in quarantined:
                QuarantinedObservation.objects.create(
                    capture=capture,
                    source_record_id=record["record_id"],
                    field_path=f"features[{index}]",
                    raw_attributes=record["attributes"],
                    reason="Invalid geometry; previous catalogue value preserved if present",
                )
            for record, geometry, capture, index, digest in staged:
                parcel, action, before, after = reconcile_parcel(
                    namespace=onwani.SOURCE_KEY, record=record, geometry=geometry
                )
                observation = ParcelObservation.objects.create(
                    parcel=parcel,
                    capture=capture,
                    source_record_id=record["record_id"],
                    field_path=f"features[{index}]",
                    raw_attributes=record["attributes"],
                    record_sha256=digest,
                    mapping_version=onwani.VERSION,
                )
                summary[action] += 1
                if action != "unchanged":
                    AuditEvent.objects.create(
                        run=run,
                        parcel=parcel,
                        observation=observation,
                        actor=actor,
                        action=action,
                        reason="Complete validated Onwani acquisition; not publicly published",
                        parcel_revision=parcel.revision,
                        before=before,
                        after=after,
                    )
            run.status = "quarantined" if quarantined else "succeeded"
            run.summary = summary
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "summary", "finished_at"])
        return run
    except Exception as exc:
        if run:
            # Error class only: do not persist credentials, raw contents or SQL in diagnostics.
            run.status = "failed"
            run.error = type(exc).__name__
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "error", "finished_at"])
        raise
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK_KEY])
