"""Allowlisted provenance reads. Raw payloads and operator identities stay internal."""

import base64
from urllib.parse import urlparse

from django.db.models import Exists, F, OuterRef, Prefetch, Q
from django.db.models.functions import Coalesce, Substr

from .models import (
    AdministrativeAreaSourceAlias,
    ImageryScene,
    MapObservation,
    ParcelObservation,
    ParcelSourceAlias,
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


def _parcel_observations(parcel_ids):
    accepted = ParcelSourceAlias.objects.filter(
        active=True,
        parcel_id=OuterRef("parcel_id"),
        source_namespace=OuterRef("parcel__source_namespace"),
        source_record_id=OuterRef("source_record_id"),
    )
    replacements = ParcelSourceAlias.objects.filter(
        active=True,
        parcel_id__in=parcel_ids,
        parcel_id=OuterRef("parcel__superseded_by_id"),
        superseded_parcel_id=OuterRef("parcel_id"),
        capture_id=OuterRef("capture_id"),
        source_namespace=OuterRef("parcel__source_namespace"),
        source_record_id=OuterRef("source_record_id"),
    )
    return (
        ParcelObservation.objects.filter(
            capture__run__source__key=F("parcel__source_namespace"),
            capture__run__status__in=["succeeded", "quarantined"],
        )
        .annotate(
            _accepted_alias=Exists(accepted),
            _accepted_replacement=Exists(replacements),
            _canonical_id=Coalesce("parcel__superseded_by_id", "parcel_id"),
        )
        .filter(
            Q(parcel_id__in=parcel_ids)
            & (Q(source_record_id=F("parcel__source_record_id")) | Q(_accepted_alias=True))
            | Q(_accepted_replacement=True)
        )
    )


def parcel_provenance(*, parcel_id, source_key):
    observation = (
        _parcel_observations([parcel_id])
        .filter(
            capture__run__source__key=source_key,
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
        _parcel_observations([parcel_id])
        .order_by("-capture__fetched_at", "-id")
        .values("raw_attributes")
        .first()
    )
    raw = observation["raw_attributes"] if observation else {}
    return {key: raw.get(key) for key in PARCEL_FIELDS}


def map_usage_tags(target, ids, capture_ids):
    """Allowlisted original OSM tags, kept internal to publication."""
    if target not in {"building", "place"}:
        return {}
    rows = MapObservation.objects.filter(
        **{f"{target}_id__in": ids},
        capture_id__in=set(capture_ids.values()),
        capture__run__status__in=["succeeded", "quarantined"],
        capture__run__source__key=F(f"{target}__source_namespace"),
    ).values(f"{target}_id", "capture_id", "raw_attributes")
    allowed = {
        "amenity",
        "building",
        "shop",
        "leisure",
        "tourism",
        "railway",
        "public_transport",
        "religion",
    }
    result = {}
    for row in rows:
        identity = str(row[f"{target}_id"])
        if row["capture_id"] != capture_ids.get(identity):
            continue
        raw = row["raw_attributes"]
        tags = raw.get("tags", {}) if isinstance(raw, dict) else {}
        if not isinstance(tags, dict):
            tags = {}
        result[identity] = {
            key: value
            for key, value in tags.items()
            if key in allowed and isinstance(value, str) and len(value) <= 255
        }
    return result


def map_provenances(target, ids, *, include_capture_id=False):
    observations = MapObservation.objects.filter(
        **{f"{target}_id__in": ids}, capture__run__status__in=["succeeded", "quarantined"]
    ).annotate(_canonical_id=F(f"{target}_id"))
    if target == "administrative_area":
        accepted = AdministrativeAreaSourceAlias.objects.filter(
            active=True,
            administrative_area_id=OuterRef("administrative_area_id"),
            source_namespace=OuterRef("administrative_area__source_namespace"),
            source_record_id=OuterRef("_provider_oid"),
        )
        replacements = AdministrativeAreaSourceAlias.objects.filter(
            active=True,
            administrative_area_id__in=ids,
            administrative_area_id=OuterRef("administrative_area__superseded_by_id"),
            superseded_area_id=OuterRef("administrative_area_id"),
            capture_id=OuterRef("capture_id"),
            source_namespace=OuterRef("administrative_area__source_namespace"),
            source_record_id=OuterRef("_provider_oid"),
        )
        observations = (
            MapObservation.objects.filter(
                capture__run__status__in=["succeeded", "quarantined"],
                capture__run__source__key=F("administrative_area__source_namespace"),
            )
            .annotate(
                _provider_oid=Substr("source_record_id", len("administrative_area:") + 1),
                _canonical_id=Coalesce(
                    "administrative_area__superseded_by_id", "administrative_area_id"
                ),
            )
            .annotate(
                _accepted_alias=Exists(accepted),
                _accepted_replacement=Exists(replacements),
            )
            .filter(
                Q(administrative_area_id__in=ids)
                & (
                    Q(_provider_oid=F("administrative_area__source_record_id"))
                    | Q(_accepted_alias=True)
                )
                | Q(_accepted_replacement=True)
            )
        )
    rows = (
        observations.order_by("_canonical_id", "-capture__fetched_at", "-id")
        .distinct("_canonical_id")
        .values(
            "_canonical_id",
            "capture_id",
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
        str(row["_canonical_id"]): {
            **({"_capture_id": row["capture_id"]} if include_capture_id else {}),
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
        _parcel_observations(parcel_ids)
        .order_by("_canonical_id", "-capture__fetched_at", "-id")
        .distinct("_canonical_id")
        .values_list("_canonical_id", "capture__run__source__url", "capture__run__source__name")
    )
    return {
        str(identity): {"url": url if urlparse(url).scheme == "https" else None, "name": name}
        for identity, url, name in rows
    }


def property_presentations(target, ids):
    """Bounded typed presentation; raw captures and reviewer identities remain private."""
    from .media_storage import delivery_url, eligible_media
    from .project_queries import project_references

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
                queryset=eligible_media()
                .select_related("capture", "mediapublication__stored_object")
                .defer("capture__payload")
                .order_by("id"),
            )
        )
        .order_by(f"{target}_id", "-capture__fetched_at", "-id")
        .distinct(f"{target}_id")
    )
    result = {}
    projects = project_references(target, ids)
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
            "project": projects.get(str(getattr(row, f"{target}_id"))),
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
                    "delivery_url": delivery_url(photo),
                }
                for photo in row.propertymedia_set.all()
            ][:4],
        }
    return result


def property_media_asset(identity):
    from .media_storage import eligible_media, read_capture

    media = (
        eligible_media()
        .select_related("capture")
        .defer("capture__payload")
        .filter(id=identity)
        .first()
    )
    if media is None:
        return None
    payload = read_capture(media.capture, max_bytes=2 * 1024 * 1024)
    if (
        len(payload) > 2 * 1024 * 1024
        or media.mime_type != "image/jpeg"
        or not payload.startswith(b"\xff\xd8\xff")
    ):
        raise ValueError("Invalid stored property image")
    return payload, media.mime_type
