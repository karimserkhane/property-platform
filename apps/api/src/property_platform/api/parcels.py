import math
from datetime import date, datetime
from uuid import UUID

from django.conf import settings
from django.db import DatabaseError
from ninja import Router, Schema, Status

from property_platform.modules.publication.uses import VERSION as USE_VERSION
from property_platform.modules.publication.uses import UseType

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
    use_types: list[UseType] = []
    use_classification_version: str = USE_VERSION
    source_url: str | None
    source_name: str | None


class Feature(Schema):
    type: str
    id: UUID
    geometry: Geometry
    properties: Properties


class Collection(Schema):
    type: str
    features: list[Feature]
    truncated: bool
    next_cursor: UUID | None = None
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
    use_types: list[UseType] = []
    use_classification_version: str = USE_VERSION
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
    response={200: list[ResearchReferenceResponse], 403: Error, 409: Error, 503: Error},
    operation_id="previewReferences",
)
def references(request, territory: str | None = None):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    from property_platform.modules.publication.coverage import profile_for, reference_source_keys

    profile = profile_for(territory) if territory else None
    if territory and profile is None:
        return Status(409, {"code": "territory_not_configured"})

    from property_platform.modules.evidence.queries import research_references

    try:
        return research_references(reference_source_keys(profile) if profile else None)
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
    response={200: list[ImageryResponse], 403: Error, 409: Error, 503: Error},
    operation_id="previewImagery",
)
def imagery(request, territory: str | None = None):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    from property_platform.modules.publication.coverage import profile_for

    profile = profile_for(territory) if territory else None
    if territory and profile is None:
        return Status(409, {"code": "territory_not_configured"})

    from property_platform.modules.evidence.queries import imagery_scenes

    try:
        return imagery_scenes(profile.imagery_ids if profile else None)
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})


class PropertyPhoto(Schema):
    id: UUID
    caption: str
    language: str
    author: str
    licence_code: str
    licence_url: str
    source_url: str
    taken_on: date | None


class PropertyPresentationResponse(Schema):
    name: str
    publisher: str
    developer: str
    website_url: str
    summary: str
    language: str
    source_url: str
    retrieved_at: datetime
    published_at: datetime | None
    media: list[PropertyPhoto]


@router.get(
    "/property-media/{media_id}",
    response={403: Error, 404: Error, 503: Error},
    operation_id="previewPropertyMedia",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Reviewed licensed JPEG; local preview only",
                "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
            }
        }
    },
)
def property_media(request, media_id: UUID):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    from django.http import HttpResponse

    from property_platform.modules.evidence.queries import property_media_asset

    try:
        media = property_media_asset(media_id)
        if media is None:
            return Status(404, {"code": "not_found"})
        payload, mime_type = media
        response = HttpResponse(payload, content_type=mime_type)
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
    except DatabaseError, ValueError:
        return Status(503, {"code": "data_unavailable"})


class MapProperties(Schema):
    id: UUID
    name: str
    name_ar: str
    kind: str
    use_types: list[UseType] = []
    use_classification_version: str = USE_VERSION
    height_m: float | None = None
    levels: int | None = None
    parcel_ids: list[UUID] = []
    source: MapProvenance
    presentation: PropertyPresentationResponse | None = None


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
    response={200: MapContext, 403: Error, 409: Error, 422: Error, 503: Error},
    operation_id="previewMapContext",
)
def context(request, bbox: str, territory: str | None = None):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    bounds = parse_bbox(bbox)
    if bounds is None:
        return Status(422, {"code": "invalid_query"})
    from property_platform.modules.publication.coverage import profile_for

    if territory and profile_for(territory) is None:
        return Status(409, {"code": "territory_not_configured"})
    if territory and not within_territory(bounds, territory):
        return Status(422, {"code": "invalid_query"})

    from property_platform.modules.publication.map_preview import map_context

    try:
        from property_platform.modules.publication.coverage import map_source_namespaces

        return map_context(
            bounds, namespaces=map_source_namespaces(territory) if territory else None
        )
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})


def enabled():
    return settings.DEBUG and getattr(settings, "PROPERTY_PLATFORM_PARCEL_PREVIEW", False)


def within_territory(bounds, territory):
    from property_platform.modules.catalog.territories import TERRITORY_BY_ID

    west, south, east, north = TERRITORY_BY_ID[territory].bounds
    return west <= bounds[0] < bounds[2] <= east and south <= bounds[1] < bounds[3] <= north


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
    response={200: Collection, 403: Error, 409: Error, 422: Error, 503: Error},
    operation_id="previewParcels",
)
def parcels(
    request,
    bbox: str,
    limit: int = 3000,
    q: str = "",
    territory: str | None = None,
    after: UUID | None = None,
):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    bounds = parse_bbox(bbox)
    query = q.strip()
    if bounds is None or not 1 <= limit <= 3000 or len(query) > 80:
        return Status(422, {"code": "invalid_query"})
    from property_platform.modules.publication.coverage import profile_for

    profile = profile_for(territory) if territory else None
    if territory and profile is None:
        return Status(409, {"code": "territory_not_configured"})
    if territory and not within_territory(bounds, territory):
        return Status(422, {"code": "invalid_query"})

    from property_platform.modules.publication.preview import features

    try:
        return features(
            bbox=bounds,
            limit=limit,
            query=query,
            after=after,
            namespaces=profile.parcel_namespaces if profile else None,
        )
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})


@router.get(
    "/parcels/{parcel_id}",
    response={200: Detail, 403: Error, 404: Error, 409: Error, 503: Error},
    operation_id="previewParcel",
)
def parcel(request, parcel_id: UUID, territory: str | None = None):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    from property_platform.modules.publication.coverage import profile_for

    profile = profile_for(territory) if territory else None
    if territory and profile is None:
        return Status(409, {"code": "territory_not_configured"})

    from property_platform.modules.publication.preview import detail

    try:
        result = detail(parcel_id, namespaces=profile.parcel_namespaces if profile else None)
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})
    if result is None:
        return Status(404, {"code": "not_found"})
    return result


class TerritoryResponse(Schema):
    id: str
    parent_id: str | None
    level: str
    name: str
    name_ar: str
    bounds: tuple[float, float, float, float]
    queryable: bool
    parcel_count: int
    camera_bounds: tuple[float, float, float, float]
    focus_bounds: tuple[float, float, float, float] | None
    neighbourhood_bounds: tuple[float, float, float, float] | None


class TerritoryRegistry(Schema):
    default_territory_id: str
    territories: list[TerritoryResponse]


@router.get(
    "/territories",
    response={200: TerritoryRegistry, 403: Error, 503: Error},
    operation_id="previewTerritories",
)
def territories(request):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    from property_platform.modules.publication.coverage import coverage_registry

    try:
        return coverage_registry()
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})


class AdrecSaleResponse(Schema):
    position: int
    registration_date: date
    project_name: str
    district: str
    community: str
    property_type: str
    property_layout: str
    sale_application_type: str
    sale_sequence: str
    price_aed: str | None
    sold_area_sqm: str | None
    plot_area_sqm: str | None
    rate_aed_per_sqm: str | None
    sold_share: str | None


class AdrecIndexResponse(Schema):
    kind: str
    property_type: str
    period_end: date
    municipality: str
    index_value: str | None


class AdrecMarketResponse(Schema):
    snapshot_id: UUID | None
    period_start: date | None
    period_end: date | None
    retrieved_at: datetime | None
    source_url: str
    total: int
    offset: int
    has_more: bool
    sales: list[AdrecSaleResponse]
    indices: list[AdrecIndexResponse]
    index_review_needed: bool


@router.get(
    "/adrec-market",
    response={200: AdrecMarketResponse, 403: Error, 422: Error, 503: Error},
    operation_id="previewAdrecMarket",
)
def adrec_market(request, territory: str, q: str = "", offset: int = 0, limit: int = 40):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    from property_platform.modules.evidence.adrec import DISTRICTS, MAX_ROWS
    from property_platform.modules.publication.adrec_preview import market

    if (
        territory not in DISTRICTS
        or len(q) > 80
        or not 0 <= offset <= MAX_ROWS
        or not 1 <= limit <= 100
    ):
        return Status(422, {"code": "invalid_query"})
    try:
        return market(territory, query=q.strip(), offset=offset, limit=limit)
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})
