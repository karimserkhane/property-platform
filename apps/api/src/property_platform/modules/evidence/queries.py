"""Allowlisted provenance reads. Raw payloads and operator identities stay internal."""

import base64
from urllib.parse import urlparse

from django.db.models import F, Prefetch

from .models import (
    ImageryScene,
    MapObservation,
    ParcelObservation,
    PropertyMedia,
    PropertyPresentation,
    ResearchReference,
)


def imagery_scenes(scene_ids=None):
    scenes = ImageryScene.objects.select_related("capture")
    if scene_ids is not None:
        scenes = scenes.filter(scene_id__in=scene_ids)
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
        for scene in scenes.order_by("-acquired_at")[:2]
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


def research_references(source_keys=None):
    records = ResearchReference.objects.all()
    if source_keys is not None:
        records = records.filter(capture__run__source__key__in=source_keys)
    rows = (
        records.order_by("capture__run__source_id", "-capture__fetched_at", "-id")
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


def parcel_sources(parcel_ids):
    rows = (
        ParcelObservation.objects.filter(
            parcel_id__in=parcel_ids,
            capture__run__source__key=F("parcel__source_namespace"),
            capture__run__status__in=["succeeded", "quarantined"],
        )
        .order_by("parcel_id", "-capture__fetched_at", "-id")
        .distinct("parcel_id")
        .values_list("parcel_id", "capture__run__source__url", "capture__run__source__name")
    )
    return {
        str(identity): {"url": url if urlparse(url).scheme == "https" else None, "name": name}
        for identity, url, name in rows
    }


def property_presentations(target, ids):
    """Bounded typed presentation; raw captures and reviewer identities remain private."""
    if target not in ("building", "place"):
        return {}
    rows = (
        PropertyPresentation.objects.filter(
            **{f"{target}_id__in": ids}, capture__run__status="succeeded"
        )
        .select_related("capture")
        .defer("capture__payload")
        .prefetch_related(
            Prefetch(
                "propertymedia_set",
                queryset=PropertyMedia.objects.filter(
                    display_allowed=True,
                    capture__parent_capture_id=F("licence_capture_id"),
                    capture__run__status="succeeded",
                    licence_capture__run__status="succeeded",
                ).order_by("id"),
            )
        )
        .order_by(f"{target}_id", "-capture__fetched_at", "-id")
        .distinct(f"{target}_id")
    )
    result = {}
    for row in rows:
        result[str(getattr(row, f"{target}_id"))] = {
            "name": row.display_name,
            "publisher": row.publisher_name,
            "developer": row.developer_name,
            "website_url": row.website_url,
            "summary": row.summary,
            "language": row.language,
            "source_url": row.capture.url,
            "retrieved_at": row.capture.fetched_at,
            "published_at": row.capture.source_published_at,
            "media": [
                {
                    "id": photo.id,
                    "caption": photo.caption,
                    "language": photo.language,
                    "author": photo.author,
                    "licence_code": photo.licence_code,
                    "licence_url": photo.licence_url,
                    "source_url": photo.source_url,
                    "taken_on": photo.taken_on,
                }
                for photo in row.propertymedia_set.all()
            ][:4],
        }
    return result


def property_media_asset(identity):
    media = (
        PropertyMedia.objects.select_related("capture")
        .filter(
            id=identity,
            display_allowed=True,
            capture__run__status="succeeded",
            capture__http_status=200,
            capture__parent_capture_id=F("licence_capture_id"),
            licence_capture__run__status="succeeded",
            licence_capture__http_status=200,
        )
        .first()
    )
    if media is None:
        return None
    payload = bytes(media.capture.payload)
    if (
        len(payload) > 2 * 1024 * 1024
        or media.mime_type != "image/jpeg"
        or not payload.startswith(b"\xff\xd8\xff")
    ):
        raise ValueError("Invalid stored property image")
    return payload, media.mime_type
