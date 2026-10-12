"""Allowlisted provenance reads. Raw payloads and operator identities stay internal."""

import base64

from .models import ImageryScene, MapObservation, ParcelObservation, ResearchReference


def imagery_scenes():
    return [
        {
            "id": scene.scene_id,
            "acquired_at": scene.acquired_at,
            "cloud_cover_tile": scene.cloud_cover_tile,
            "resolution_m": scene.resolution_m,
            "coordinates": [
                [scene.west, scene.north],
                [scene.east, scene.north],
                [scene.east, scene.south],
                [scene.west, scene.south],
            ],
            "image_url": "data:image/png;base64," + base64.b64encode(scene.preview_png).decode(),
            "source_url": scene.capture.url,
            "retrieved_at": scene.capture.fetched_at,
        }
        for scene in ImageryScene.objects.select_related("capture").order_by("-acquired_at")[:2]
    ]


def parcel_provenance(*, parcel_id, source_key):
    observation = (
        ParcelObservation.objects.filter(
            parcel_id=parcel_id,
            capture__run__source__key=source_key,
            capture__run__status__in=["succeeded", "quarantined"],
        )
        .order_by("-capture__fetched_at", "-id")
        .values(
            "capture__run__source__name",
            "capture__run__source__url",
            "capture__fetched_at",
            "source_published_at",
            "ingested_at",
        )
        .first()
    )
    if observation is None:
        return None
    return {
        "name": observation["capture__run__source__name"],
        "url": observation["capture__run__source__url"],
        "retrieved_at": observation["capture__fetched_at"],
        "published_at": observation["source_published_at"],
        "ingested_at": observation["ingested_at"],
    }


PARCEL_FIELDS = (
    "PLANNINGSTATUS",
    "OWNERSHIPTYPE",
    "ELMS_AllocationStatus",
    "APPROVALDATE",
    "DataReceivedDate",
    "Permit_LastDate",
    "Permit_LastType",
    "MEPS_CONS_STATUS",
    "MEPS_CONS_UPDATEON",
    "DMT_DCR_URL",
    "ELMS_LANDUSENAME_A",
)


def parcel_attributes(parcel_id):
    observation = (
        ParcelObservation.objects.filter(
            parcel_id=parcel_id, capture__run__status__in=["succeeded", "quarantined"]
        )
        .order_by("-capture__fetched_at", "-id")
        .values("raw_attributes")
        .first()
    )
    raw = observation["raw_attributes"] if observation else {}
    return {key: raw.get(key) for key in PARCEL_FIELDS}


def map_provenances(target, ids):
    rows = (
        MapObservation.objects.filter(
            **{f"{target}_id__in": ids}, capture__run__status__in=["succeeded", "quarantined"]
        )
        .order_by(f"{target}_id", "-capture__fetched_at", "-id")
        .distinct(f"{target}_id")
        .values(
            f"{target}_id",
            "source_url",
            "source_published_at",
            "ingested_at",
            "capture__fetched_at",
            "capture__run__source__name",
            "capture__run__source__key",
            "capture__acquisition_method",
            "capture__timestamp_basis",
            "capture__researchreference__source_kind",
        )
    )
    return {
        str(row[f"{target}_id"]): {
            "url": row["source_url"],
            "name": row["capture__run__source__name"],
            "retrieved_at": row["capture__fetched_at"],
            "published_at": row["source_published_at"],
            "ingested_at": row["ingested_at"],
            "reliability": "official"
            if row["capture__run__source__key"].startswith("dmt:")
            else "community"
            if row["capture__run__source__key"].startswith("osm:")
            else "broker"
            if row["capture__researchreference__source_kind"] == "broker"
            else "publisher",
            "acquisition_method": row["capture__acquisition_method"],
            "timestamp_basis": row["capture__timestamp_basis"],
        }
        for row in rows
    }


def research_references():
    rows = (
        ResearchReference.objects.order_by("capture__run__source_id", "-capture__fetched_at", "-id")
        .distinct("capture__run__source_id")
        .values(
            "label",
            "page_title",
            "source_kind",
            "available",
            "place_id",
            "capture__run__source__url",
            "capture__fetched_at",
            "capture__source_published_at",
        )[:200]
    )
    return [
        {
            "label": row["label"],
            "title": row["page_title"],
            "source_kind": row["source_kind"],
            "available": row["available"],
            "place_id": row["place_id"],
            "url": row["capture__run__source__url"],
            "retrieved_at": row["capture__fetched_at"],
            "published_at": row["capture__source_published_at"],
        }
        for row in rows
    ]
