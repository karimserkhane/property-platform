import math
from datetime import datetime
from uuid import UUID

from django.conf import settings
from django.db import DatabaseError
from ninja import Router, Schema, Status

router = Router(tags=["local-preview"])


class Error(Schema):
    code: str


class Geometry(Schema):
    type: str
    coordinates: list[list[list[list[float]]]]


class Properties(Schema):
    id: UUID
    code: str
    community: str


class Feature(Schema):
    type: str
    id: UUID
    geometry: Geometry
    properties: Properties


class Collection(Schema):
    type: str
    features: list[Feature]
    truncated: bool


class Provenance(Schema):
    name: str
    url: str
    retrieved_at: datetime
    published_at: datetime | None
    ingested_at: datetime


class Detail(Schema):
    id: UUID
    code: str
    district: str
    community: str
    revision: int
    source: Provenance
    publication_status: str


def enabled():
    return settings.DEBUG and getattr(settings, "LIWA_PARCEL_PREVIEW", False)


def parse_bbox(value):
    try:
        bounds = tuple(float(part) for part in value.split(","))
    except ValueError:
        return None
    if len(bounds) != 4 or not all(math.isfinite(v) for v in bounds):
        return None
    west, south, east, north = bounds
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        return None
    if east - west > 0.2 or north - south > 0.2:
        return None
    return bounds


@router.get(
    "/parcels",
    response={200: Collection, 403: Error, 422: Error, 503: Error},
    operation_id="previewParcels",
)
def parcels(request, bbox: str, limit: int = 3000, q: str = ""):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    bounds = parse_bbox(bbox)
    query = q.strip()
    if bounds is None or not 1 <= limit <= 3000 or len(query) > 80:
        return Status(422, {"code": "invalid_query"})
    from liwa.modules.publication.preview import features

    try:
        return features(bbox=bounds, limit=limit, query=query)
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})


@router.get(
    "/parcels/{parcel_id}",
    response={200: Detail, 403: Error, 404: Error, 503: Error},
    operation_id="previewParcel",
)
def parcel(request, parcel_id: UUID):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    from liwa.modules.publication.preview import detail

    try:
        result = detail(parcel_id)
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})
    if result is None:
        return Status(404, {"code": "not_found"})
    return result
