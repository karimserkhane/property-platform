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
    land_use: str
    construction_status: str
    category: str


class Feature(Schema):
    type: str
    id: UUID
    geometry: Geometry
    properties: Properties


class Collection(Schema):
    type: str
    features: list[Feature]
    truncated: bool
    classification_version: str


class Provenance(Schema):
    name: str
    url: str
    retrieved_at: datetime
    published_at: datetime | None
    ingested_at: datetime


class ParcelAttributes(Schema):
    planning: str
    ownership: str
    allocation: str
    approval_date: str | None
    received_date: str | None
    permit_date: str | None
    permit_type: str
    meps: str
    meps_updated: str
    dcr_url: str


class NearbyPlace(Schema):
    id: UUID
    name: str
    name_ar: str
    kind: str


class NearbyStreet(Schema):
    id: UUID
    name: str
    name_ar: str
    distance_m: float


class Detail(Schema):
    id: UUID
    code: str
    district: str
    community: str
    revision: int
    source: Provenance
    publication_status: str
    land_use: str
    construction_status: str
    category: str
    area_m2: float
    attributes: ParcelAttributes
    places: list[NearbyPlace]
    streets: list[NearbyStreet]


class MapProvenance(Provenance):
    reliability: str
    acquisition_method: str
    timestamp_basis: str


class ResearchReferenceResponse(Schema):
    label: str
    title: str
    source_kind: str
    available: bool
    place_id: UUID | None
    url: str
    retrieved_at: datetime
    published_at: datetime | None


@router.get(
    "/references",
    response={200: list[ResearchReferenceResponse], 403: Error, 503: Error},
    operation_id="previewReferences",
)
def references(request):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    from property_platform.modules.evidence.queries import research_references

    try:
        return research_references()
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})


class ImageryResponse(Schema):
    id: str
    acquired_at: datetime
    cloud_cover_tile: float
    resolution_m: int
    coordinates: list[list[float]]
    image_url: str
    source_url: str
    retrieved_at: datetime


@router.get(
    "/imagery",
    response={200: list[ImageryResponse], 403: Error, 503: Error},
    operation_id="previewImagery",
)
def imagery(request):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    from property_platform.modules.evidence.queries import imagery_scenes

    try:
        return imagery_scenes()
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})


class MapProperties(Schema):
    id: UUID
    name: str
    name_ar: str
    kind: str
    height_m: float | None = None
    levels: int | None = None
    parcel_ids: list[UUID] = []
    source: MapProvenance


class LineGeometry(Schema):
    type: str
    coordinates: list[list[list[float]]]


class PointGeometry(Schema):
    type: str
    coordinates: list[float]


class MapFeature(Schema):
    type: str
    id: UUID
    geometry: Geometry | LineGeometry | PointGeometry
    properties: MapProperties


class MapCollection(Schema):
    type: str
    features: list[MapFeature]
    truncated: bool


class MapContext(Schema):
    street: MapCollection
    building: MapCollection
    place: MapCollection
    administrative_area: MapCollection


@router.get(
    "/map-context",
    response={200: MapContext, 403: Error, 422: Error, 503: Error},
    operation_id="previewMapContext",
)
def context(request, bbox: str):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    bounds = parse_bbox(bbox)
    if bounds is None:
        return Status(422, {"code": "invalid_query"})
    from property_platform.modules.publication.map_preview import map_context

    try:
        return map_context(bounds)
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})


def enabled():
    return settings.DEBUG and getattr(settings, "PROPERTY_PLATFORM_PARCEL_PREVIEW", False)


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
    from property_platform.modules.publication.preview import features

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
    from property_platform.modules.publication.preview import detail

    try:
        result = detail(parcel_id)
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})
    if result is None:
        return Status(404, {"code": "not_found"})
    return result
