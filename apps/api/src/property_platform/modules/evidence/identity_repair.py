"""Reviewable reconciliation of already persisted provider-ID duplicates; no deletion."""

import hashlib
import json

from django.db import connection, transaction
from django.utils import timezone

from property_platform.modules.catalog.models import AdministrativeArea, Parcel
from property_platform.modules.catalog.services import (
    geometry_from_rings,
    restore_superseded_identity,
    supersede_administrative_area,
    supersede_parcel,
)

from . import map_sources, onwani
from .collection_profiles import COLLECTIONS
from .identity_resolution import (
    IdentityConflict,
    area_attributes,
    non_oid_attributes,
    parcel_values_match,
)
from .models import (
    AdministrativeAreaSourceAlias,
    IngestionRun,
    MapObservation,
    ParcelObservation,
    ParcelSourceAlias,
)

SUPPORTED_AREAS = {
    p.map_namespace(layer) for p in COLLECTIONS.values() for layer in ("district", "community")
}


def _actor(actor):
    if not isinstance(actor, str) or not 1 <= len(actor.strip()) <= 160:
        raise ValueError("Valid actor required")
    return actor.strip()


def _features(capture, cache):
    if capture.id not in cache:
        payload = bytes(capture.payload)
        if (
            capture.http_status != 200
            or hashlib.sha256(payload).hexdigest() != capture.content_sha256
        ):
            raise IdentityConflict("Stored capture is not a successful verified source response")
        data = json.loads(payload)
        if data.get("spatialReference", {}).get("wkid") != 4326:
            raise IdentityConflict("Stored capture has an unexpected CRS")
        features = data.get("features")
        if not isinstance(features, list):
            raise IdentityConflict("Stored capture has no source features")
        cache[capture.id] = {
            str(feature["attributes"]["OBJECTID"]): feature for feature in features
        }
        if len(cache[capture.id]) != len(features):
            raise IdentityConflict("Stored capture has duplicate provider identities")
    return cache[capture.id]


def _plan(run):
    namespace, cache, actions = run.source.key, {}, []
    counts = {"candidates": 0, "already_resolved": 0, "unchanged": 0, "conflicts": 0}
    profile = next((p for p in COLLECTIONS.values() if p.parcel_namespace == namespace), None)
    if profile is not None:
        target, alias_model = Parcel, ParcelSourceAlias
        observations = (
            ParcelObservation.objects.filter(capture__run=run)
            .select_related("parcel", "capture")
            .defer("capture__payload")
            .order_by("pk")
        )
        records = list(
            Parcel.objects.filter(source_namespace=namespace, superseded_by__isnull=True)
        )
        for observation in observations:
            duplicate = observation.parcel
            feature = _features(observation.capture, cache).get(observation.source_record_id)
            if feature is None or feature["attributes"] != observation.raw_attributes:
                raise IdentityConflict("Parcel observation disagrees with its source capture")
            record = onwani.parse_feature(feature, territory=profile.territory)
            shape = geometry_from_rings(record["rings"])
            alias = alias_model.objects.filter(
                source_namespace=namespace, source_record_id=record["record_id"], active=True
            ).first()
            if alias is not None and duplicate.superseded_by_id == alias.parcel_id:
                counts["already_resolved"] += 1
                continue
            if duplicate.superseded_by_id is not None or not parcel_values_match(
                duplicate, record, shape
            ):
                counts["conflicts"] += 1
                continue
            candidates = [
                item
                for item in records
                if item.id != duplicate.id
                and item.created_at < duplicate.created_at
                and parcel_values_match(item, record, shape)
            ]
            if not candidates:
                counts["unchanged"] += 1
                continue
            if len(candidates) != 1 or alias is not None:
                counts["conflicts"] += 1
                continue
            actions.append((duplicate, candidates[0], observation.capture, record["record_id"]))
            counts["candidates"] += 1
    elif namespace in SUPPORTED_AREAS:
        target, alias_model = AdministrativeArea, AdministrativeAreaSourceAlias
        observations = (
            MapObservation.objects.filter(capture__run=run, administrative_area__isnull=False)
            .select_related("administrative_area", "capture")
            .defer("capture__payload")
            .order_by("pk")
        )
        records = list(
            AdministrativeArea.objects.filter(
                source_namespace=namespace, superseded_by__isnull=True
            )
        )
        prior = {item.id: area_attributes(item) for item in records}
        for observation in observations:
            duplicate = observation.administrative_area
            oid = observation.source_record_id.removeprefix("administrative_area:")
            feature = _features(observation.capture, cache).get(oid)
            if feature is None or feature["attributes"] != observation.raw_attributes:
                raise IdentityConflict("Area observation disagrees with its source capture")
            attrs = feature["attributes"]
            shape = geometry_from_rings(
                [
                    map_sources.coordinates(ring, closed=True)
                    for ring in feature["geometry"]["rings"]
                ]
            )
            alias = alias_model.objects.filter(
                source_namespace=namespace, source_record_id=oid, active=True
            ).first()
            if alias is not None and duplicate.superseded_by_id == alias.administrative_area_id:
                counts["already_resolved"] += 1
                continue
            if duplicate.superseded_by_id is not None or not duplicate.geometry.equals(shape):
                counts["conflicts"] += 1
                continue
            candidates = [
                item
                for item in records
                if item.id != duplicate.id
                and item.created_at < duplicate.created_at
                and item.kind == duplicate.kind
                and item.geometry.equals(shape)
                and prior[item.id] == non_oid_attributes(attrs)
            ]
            if not candidates:
                counts["unchanged"] += 1
                continue
            if len(candidates) != 1 or alias is not None:
                counts["conflicts"] += 1
                continue
            actions.append((duplicate, candidates[0], observation.capture, oid))
            counts["candidates"] += 1
    else:
        raise ValueError("Only reviewed Onwani parcel/administrative providers can be reconciled")
    report = {
        "run_id": str(run.id),
        "namespace": namespace,
        "target": "parcel" if target is Parcel else "administrative_area",
        **counts,
        "applied": False,
        "samples": [
            {
                "duplicate_id": str(duplicate.pk),
                "canonical_id": str(canonical.pk),
                "object_id": oid,
                "capture_id": capture.id,
            }
            for duplicate, canonical, capture, oid in actions[:3]
        ],
    }
    return report, actions, target, alias_model


def repair_source_identities(*, run_id, actor, apply=False):
    actor = _actor(actor)
    if connection.vendor != "postgresql":
        raise ValueError("Identity reconciliation requires PostgreSQL/PostGIS")
    locks = []
    try:
        for lock in (716548219, 716548220):
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_lock(%s)", [lock])
                if not cursor.fetchone()[0]:
                    raise IdentityConflict("Source import is running; review after completion")
                locks.append(lock)
        with transaction.atomic():
            run = IngestionRun.objects.select_related("source").get(id=run_id)
            if run.status not in {"succeeded", "quarantined"}:
                raise IdentityConflict("A completed source acquisition is required")
            report, actions, target, alias_model = _plan(run)
            if apply:
                if report["conflicts"]:
                    raise IdentityConflict("Ambiguous source identities; no repair was applied")
                for duplicate, canonical, capture, oid in actions:
                    if target is Parcel:
                        supersede_parcel(duplicate_id=duplicate.pk, canonical_id=canonical.pk)
                        fields = {"parcel": canonical, "superseded_parcel": duplicate}
                    else:
                        supersede_administrative_area(
                            duplicate_id=duplicate.pk, canonical_id=canonical.pk
                        )
                        fields = {"administrative_area": canonical, "superseded_area": duplicate}
                    alias_model.objects.create(
                        source_namespace=run.source.key,
                        source_record_id=oid,
                        capture=capture,
                        actor=actor,
                        canonical_revision=canonical.revision,
                        superseded_revision=duplicate.revision + 1,
                        reason=(
                            "Reviewed existing duplicate: same provider stable identity "
                            "and exact source geometry"
                        ),
                        **fields,
                    )
                report["applied"] = True
            return report
    finally:
        for lock in reversed(locks):
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [lock])


def reverse_identity_decision(*, target, decision_id, actor, reason, apply=False):
    actor = _actor(actor)
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 255:
        raise ValueError("A review reason is required for reversal")
    choices = {
        "parcel": (ParcelSourceAlias, Parcel, "parcel", "superseded_parcel"),
        "administrative_area": (
            AdministrativeAreaSourceAlias,
            AdministrativeArea,
            "administrative_area",
            "superseded_area",
        ),
    }
    if target not in choices:
        raise ValueError("Unknown identity decision target")
    alias_model, model, canonical_field, duplicate_field = choices[target]
    with transaction.atomic():
        with connection.cursor() as cursor:
            for lock in (716548219, 716548220):
                cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", [lock])
                if not cursor.fetchone()[0]:
                    raise IdentityConflict("Source import is running; review after completion")
        decision = alias_model.objects.select_for_update().get(pk=decision_id)
        canonical_id = getattr(decision, canonical_field + "_id")
        duplicate_id = getattr(decision, duplicate_field + "_id")
        if decision.active:
            canonical = model.objects.select_for_update().get(pk=canonical_id)
            if (
                canonical.superseded_by_id is not None
                or canonical.revision != decision.canonical_revision
            ):
                raise IdentityConflict(
                    "Canonical attributes changed after the decision; review before reversal"
                )
            if duplicate_id is not None:
                duplicate = model.objects.select_for_update().get(pk=duplicate_id)
                if duplicate.revision != decision.superseded_revision:
                    raise IdentityConflict(
                        "Duplicate attributes changed after the decision; review before reversal"
                    )
        if apply and decision.active:
            if duplicate_id is not None:
                restore_superseded_identity(
                    model=model, duplicate_id=duplicate_id, canonical_id=canonical_id
                )
            decision.active, decision.revoked_at = False, timezone.now()
            decision.revoked_by, decision.revocation_reason = actor, reason.strip()
            decision.save(update_fields=["active", "revoked_at", "revoked_by", "revocation_reason"])
        return {
            "target": target,
            "decision_id": decision.pk,
            "applied": apply,
            "active": decision.active,
            "canonical_id": str(canonical_id),
            "duplicate_id": str(duplicate_id) if duplicate_id else None,
        }
