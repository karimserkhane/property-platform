"""Preserve AD-SDI evidence, fill uncovered plots, and compare without overwriting Onwani."""

import hashlib
import json

from django.db import connection, transaction
from django.utils import timezone

from property_platform.modules.catalog.models import Parcel
from property_platform.modules.catalog.services import geometry_from_rings, reconcile_parcel

from ..models import (
    AuditEvent,
    Capture,
    IngestionRun,
    ParcelObservation,
    QuarantinedObservation,
    Source,
)
from ..runs import mark_failed
from . import sdi_protocol as protocol
from .onwani import SourceError


def import_parcels(*, territory, actor, acquisition):
    """`territory` is an island profile or a reviewed emirate district scope (`adm:<slug>`)."""
    if connection.vendor != "postgresql":
        raise ValueError("AD-SDI requires real PostGIS")
    municipality, _ = protocol.scope_for(territory)
    source, _ = Source.objects.get_or_create(
        key=protocol.namespace(territory),
        defaults={"name": f"AD-SDI / Plots — {territory}", "url": protocol.URL},
    )
    run = IngestionRun.objects.create(
        source=source, connector_version=protocol.VERSION, actor=actor
    )
    try:

        def acquire(base, params):
            payload, receipt = acquisition(base, params)
            capture = Capture.objects.create(
                run=run,
                payload=payload,
                byte_length=len(payload),
                content_sha256=hashlib.sha256(payload).hexdigest(),
                **receipt,
            )
            if receipt["http_status"] != 200:
                raise SourceError("AD-SDI HTTP failure")
            return protocol.decode(payload), capture

        meta, _ = acquire(protocol.URL, {"f": "pjson"})
        uses = protocol.metadata(meta)
        listing_params = {"f": "json", "where": protocol.where(territory), "returnIdsOnly": "true"}
        listing, _ = acquire(protocol.URL + "/query", listing_params)
        ids = protocol.object_ids(listing)
        staged, seen, plot_ids = [], set(), set()
        for offset in range(0, len(ids), 100):
            batch_ids = ids[offset : offset + 100]
            batch, capture = acquire(
                protocol.URL + "/query",
                {
                    "f": "json",
                    "where": protocol.where(territory),
                    "objectIds": ",".join(map(str, batch_ids)),
                    "outFields": protocol.FIELDS,
                    "returnGeometry": "true",
                    "outSR": "4326",
                },
            )
            if batch.get("spatialReference", {}).get("wkid") != 4326:
                raise SourceError("AD-SDI batch CRS mismatch")
            if not isinstance(batch.get("features"), list):
                raise SourceError("AD-SDI batch missing features")
            for index, feature in enumerate(batch["features"]):
                oid = feature.get("attributes", {}).get("OBJECTID")
                if oid not in batch_ids or oid in seen:
                    raise SourceError("AD-SDI batch identity mismatch")
                seen.add(oid)
                record = protocol.parse(feature, territory, uses)
                if record["record_id"] in plot_ids:
                    raise SourceError("Ambiguous duplicate official plot identity")
                plot_ids.add(record["record_id"])
                try:
                    geometry = geometry_from_rings(record["rings"])
                except ValueError:
                    geometry = None
                digest = hashlib.sha256(
                    json.dumps(feature, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                staged.append((record, geometry, capture, index, digest))
            if not set(batch_ids).issubset(seen):
                raise SourceError("Incomplete AD-SDI batch")
        latest, _ = acquire(protocol.URL + "/query", listing_params)
        if protocol.object_ids(latest) != ids or seen != set(ids):
            raise SourceError("AD-SDI coverage changed during acquisition")
        summary = {
            key: 0
            for key in (
                "created",
                "updated",
                "unchanged",
                "compared",
                "consistent",
                "geometry_conflict",
                "quarantined",
            )
        }
        summary["observed"] = len(seen)
        with transaction.atomic():
            for record, geometry, capture, index, digest in staged:
                candidates = list(
                    Parcel.objects.select_for_update().filter(
                        superseded_by__isnull=True,
                        official_plot_id=record["record_id"],
                        municipality=municipality,
                        district=record["values"]["district"],
                    )[:2]
                )
                reason = None
                if geometry is None:
                    reason = "Invalid AD-SDI geometry; existing geometry preserved"
                elif len(candidates) > 1:
                    reason = "Ambiguous existing official plot identity; manual review required"
                elif candidates and candidates[0].source_namespace != source.key:
                    a = candidates[0].geometry.transform(32640, clone=True)
                    b = geometry.transform(32640, clone=True)
                    union = a.union(b).area
                    overlap = a.intersection(b).area / union if union else 0
                    summary["compared"] += 1
                    if overlap < 0.98:
                        summary["geometry_conflict"] += 1
                        reason = "Same plot ID, divergent geometry; existing shape preserved"
                    else:
                        summary["consistent"] += 1
                elif not candidates:
                    # Different IDs can represent older subdivisions or another ID system.
                    # Never publish a second almost-identical polygon by inferring a merge.
                    nearby = list(
                        Parcel.objects.filter(
                            superseded_by__isnull=True,
                            municipality=municipality,
                            district=record["values"]["district"],
                            geometry__intersects=geometry,
                        ).exclude(source_namespace=source.key)[:65]
                    )
                    if len(nearby) > 64:
                        reason = "Too many overlapping source parcels; explicit review required"
                    else:
                        b = geometry.transform(32640, clone=True)
                        for other in nearby:
                            a = other.geometry.transform(32640, clone=True)
                            union = a.union(b).area
                            if union and a.intersection(b).area / union >= 0.98:
                                reason = "Different IDs, nearly identical geometry; review required"
                                break
                if reason:
                    QuarantinedObservation.objects.create(
                        capture=capture,
                        source_record_id=record["record_id"],
                        field_path=f"features[{index}]",
                        raw_attributes=record["attributes"],
                        reason=reason,
                    )
                    summary["quarantined"] += 1
                    continue
                parcel = candidates[0] if candidates else None
                action, before, after = "unchanged", {}, {}
                # Matching evidence never replaces the richer provider's canonical fields.
                if parcel is None or parcel.source_namespace == source.key:
                    parcel, action, before, after = reconcile_parcel(
                        namespace=source.key,
                        record=record,
                        geometry=geometry,
                        canonical_id=parcel.pk if parcel else None,
                    )
                observation = ParcelObservation.objects.create(
                    parcel=parcel,
                    capture=capture,
                    source_record_id=record["record_id"],
                    field_path=f"features[{index}]",
                    raw_attributes=record["attributes"],
                    record_sha256=digest,
                    mapping_version=protocol.VERSION,
                )
                summary[action] += 1
                if action != "unchanged":
                    AuditEvent.objects.create(
                        run=run,
                        parcel=parcel,
                        observation=observation,
                        actor=actor,
                        action=action,
                        reason="AD-SDI parcel; private preview; no inferred project identity",
                        parcel_revision=parcel.revision,
                        before=before,
                        after=after,
                    )
            run.status = "quarantined" if summary["quarantined"] else "succeeded"
            run.summary, run.finished_at = summary, timezone.now()
            run.save(update_fields=["status", "summary", "finished_at"])
        return run
    except Exception as exc:
        mark_failed(run, exc)
        raise
