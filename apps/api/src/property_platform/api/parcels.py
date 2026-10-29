import math
from datetime import date, datetime
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from ninja import Router, Schema, Status
from ninja.decorators import decorate_view

from property_platform.modules.publication.uses import VERSION as USE_VERSION
from property_platform.modules.publication.uses import UseType

from .preview import territory_profile
from .read_cache import cached_read

router = Router(tags=["local-preview"])


class Error(Schema):
    code: str


class SourceRightsResponse(Schema):
    """Reviewed rights of the source site (A19); `unknown` means not qualified yet."""

    licence: str
    licence_url: str | None = None
    terms_url: str | None = None
    publication: Literal["open", "facts", "link", "none"]
    attribution: str | None = None
    reviewed_on: date | None = None
    shown_beyond_terms: bool = False


def _value(row, field):
    return row.get(field) if isinstance(row, dict) else getattr(row, field, None)


def cited_rights(row, field):
    """The rights of the page a response cites in `field`, for every cited source (A24)."""
    from property_platform.modules.evidence.source_rights import public_rights

    url = _value(row, field)
    return public_rights(url) if url else None


class CitedSourceResponse(Schema):
    """One site cited by a list of map features, with its reviewed rights (A24).

    `host` is the reviewed registry host covering the site (or the page's own host when
    no review lists it); a feature's rights are those of the entry covering its URL.
    `url` and `name` are the first page of that site the list cites.
    """

    host: str
    url: str
    name: str
    rights: SourceRightsResponse


def cited_sources(collection, source):
    """One entry per site a feature list cites, so its thousands of features need no rights.

    Map features cite one page each (an OpenStreetMap way, a register record), but
    rights belong to the site: every page of a reviewed host shares its review.
    """
    from property_platform.modules.evidence.source_rights import public_rights, rights_for

    found = {}
    for feature in _value(collection, "features") or ():
        url, name = source(_value(feature, "properties") or {})
        if not url:
            continue
        host = rights_for(url)["host"] or (urlsplit(url).hostname or "").lower()
        if host and host not in found:
            found[host] = {
                "host": host,
                "url": url,
                "name": name or "",
                "rights": public_rights(url),
            }
    return list(found.values())


def _parcel_source(properties):
    return _value(properties, "source_url"), _value(properties, "source_name")


def _map_source(properties):
    source = _value(properties, "source") or {}
    return _value(source, "url"), _value(source, "name")


class Geometry(Schema):
    type: str
    coordinates: list[list[list[list[float]]]]


class FieldHistory(Schema):
    url: str
    retrieved_at: datetime
    ingested_at: datetime
    rights: SourceRightsResponse | None = None

    @staticmethod
    def resolve_rights(obj):
        return cited_rights(obj, "url")


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
    field_history: dict[str, FieldHistory] = {}


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
    sources: list[CitedSourceResponse] = []

    @staticmethod
    def resolve_sources(obj):
        return cited_sources(obj, _parcel_source)


class NearbyProjectMarker(Schema):
    place_id: UUID
    distance_m: float


class IndexProperties(Properties):
    bounds: tuple[float, float, float, float]
    label_point: tuple[float, float]
    area_m2: float
    nearby_projects: list[NearbyProjectMarker] = []


class IndexFeature(Schema):
    type: str
    id: UUID
    properties: IndexProperties


class ParcelIndex(Schema):
    type: str
    features: list[IndexFeature]
    truncated: bool
    next_cursor: UUID | None = None
    classification_version: str
    sources: list[CitedSourceResponse] = []

    @staticmethod
    def resolve_sources(obj):
        return cited_sources(obj, _parcel_source)


class Provenance(Schema):
    name: str
    url: str
    retrieved_at: datetime
    published_at: datetime | None
    ingested_at: datetime
    rights: SourceRightsResponse | None = None

    @staticmethod
    def resolve_rights(obj):
        return cited_rights(obj, "url")


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


class OverlappingParcel(Schema):
    id: UUID
    code: str
    land_use: str
    use_types: list[UseType]
    construction_status: str
    ownership: str
    source: Provenance


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
    overlapping_parcels: list[OverlappingParcel]
    field_history: dict[str, FieldHistory] = {}


class MapProvenance(Schema):
    """Provenance of one map feature; its rights are in the list's `sources` (A24)."""

    name: str
    url: str
    retrieved_at: datetime
    published_at: datetime | None
    ingested_at: datetime
    reliability: str
    acquisition_method: str
    timestamp_basis: str


class CitedMapProvenance(MapProvenance):
    rights: SourceRightsResponse | None = None

    @staticmethod
    def resolve_rights(obj):
        return cited_rights(obj, "url")


class Amenity(Schema):
    id: UUID
    name: str
    name_ar: str
    use_types: list[UseType]
    distance_m: float
    source: CitedMapProvenance


class AmenityGroup(Schema):
    key: Literal["education", "shopping", "health", "transport", "leisure", "dining", "worship"]
    items: list[Amenity]


class Surroundings(Schema):
    radius_m: int
    distance_basis: Literal["point", "centroid"]
    truncated: bool
    groups: list[AmenityGroup]


@router.get(
    "/surroundings/{target}/{identity}",
    response={200: Surroundings, 403: Error, 404: Error, 409: Error, 503: Error},
    operation_id="previewSurroundings",
)
@decorate_view(cached_read)
def surroundings(
    request,
    target: Literal["parcel", "building", "place", "street"],
    identity: UUID,
    territory: str | None = None,
):
    profile = territory_profile(territory)
    from property_platform.modules.publication.coverage import map_source_namespaces
    from property_platform.modules.publication.surroundings import surroundings as project

    result = project(
        target,
        identity,
        namespaces=map_source_namespaces(territory) if territory else None,
        parcel_namespaces=profile.parcel_namespaces if profile else None,
    )
    if result is None:
        return Status(404, {"code": "not_found"})
    return result


class ResearchReferenceResponse(Schema):
    label: str
    title: str
    source_kind: str
    available: bool
    place_id: UUID | None
    url: str
    retrieved_at: datetime
    published_at: datetime | None
    rights: SourceRightsResponse | None = None

    @staticmethod
    def resolve_rights(obj):
        return cited_rights(obj, "url")


@router.get(
    "/references",
    response={200: list[ResearchReferenceResponse], 403: Error, 409: Error, 503: Error},
    operation_id="previewReferences",
)
@decorate_view(cached_read)
def references(request, territory: str | None = None):
    profile = territory_profile(territory)
    from property_platform.modules.evidence.projects.queries import research_references
    from property_platform.modules.publication.coverage import reference_source_keys

    return research_references(reference_source_keys(profile) if profile else None)


class ImageryResponse(Schema):
    id: str
    acquired_at: datetime
    cloud_cover_tile: float
    resolution_m: int
    coordinates: list[list[float]]
    image_url: str
    source_url: str
    retrieved_at: datetime
    rights: SourceRightsResponse | None = None

    @staticmethod
    def resolve_rights(obj):
        return cited_rights(obj, "source_url")


@router.get(
    "/imagery",
    response={200: list[ImageryResponse], 403: Error, 409: Error, 503: Error},
    operation_id="previewImagery",
)
@decorate_view(cached_read)
def imagery(request, territory: str | None = None):
    profile = territory_profile(territory)
    from property_platform.modules.evidence.projects.queries import imagery_scenes

    return imagery_scenes(profile.imagery_ids if profile else None)


class PropertyPhoto(Schema):
    id: UUID
    caption: str
    language: str
    author: str
    licence_code: str
    licence_url: str
    source_url: str
    taken_on: date | None
    delivery_url: str | None = None


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
    project: ProjectReferenceResponse | None = None
    rights: SourceRightsResponse | None = None

    @staticmethod
    def resolve_rights(obj):
        return cited_rights(obj, "source_url")


class ProjectReferenceResponse(Schema):
    id: UUID
    slug: str
    name: str


PropertyPresentationResponse.model_rebuild()


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
    from django.http import HttpResponse

    from property_platform.modules.evidence.projects.queries import property_media_asset

    try:
        media = property_media_asset(media_id)
    except ValueError:
        return Status(503, {"code": "data_unavailable"})
    if media is None:
        return Status(404, {"code": "not_found"})
    payload, mime_type = media
    response = HttpResponse(payload, content_type=mime_type)
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


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
    field_history: dict[str, FieldHistory] = {}


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
    sources: list[CitedSourceResponse] = []

    @staticmethod
    def resolve_sources(obj):
        return cited_sources(obj, _map_source)


class MapContext(Schema):
    street: MapCollection
    building: MapCollection
    place: MapCollection
    administrative_area: MapCollection


class ContextIndexProperties(MapProperties):
    bounds: tuple[float, float, float, float]


class ContextIndexFeature(Schema):
    type: str
    id: UUID
    properties: ContextIndexProperties


class ContextIndexCollection(Schema):
    type: str
    features: list[ContextIndexFeature]
    truncated: bool
    sources: list[CitedSourceResponse] = []

    @staticmethod
    def resolve_sources(obj):
        return cited_sources(obj, _map_source)


class ContextIndex(Schema):
    street: ContextIndexCollection
    building: ContextIndexCollection
    place: MapCollection
    administrative_area: MapCollection


@router.get(
    "/map-context",
    response={200: MapContext, 403: Error, 409: Error, 422: Error, 503: Error},
    operation_id="previewMapContext",
)
@decorate_view(cached_read)
def context(request, bbox: str, territory: str | None = None):
    return _context(bbox, territory)


@router.get(
    "/context-index",
    response={200: ContextIndex, 403: Error, 409: Error, 422: Error, 503: Error},
    operation_id="previewContextIndex",
)
@decorate_view(cached_read)
def context_index(request, bbox: str, territory: str | None = None):
    """`map-context` rows; streets and buildings come with bounds instead of
    geometry, for maps drawing them from `context-tiles`."""
    return _context(bbox, territory, tiled=True)


def _context(bbox, territory, *, tiled=False):
    bounds = parse_bbox(bbox)
    if bounds is None:
        return Status(422, {"code": "invalid_query"})
    profile = territory_profile(territory)
    if territory and not within_territory(bounds, territory):
        return Status(422, {"code": "invalid_query"})

    from property_platform.modules.publication.coverage import map_source_namespaces
    from property_platform.modules.publication.map_preview import map_context

    return map_context(
        bounds,
        namespaces=map_source_namespaces(territory) if territory else None,
        parcel_namespaces=profile.parcel_namespaces if profile else None,
        tiled=tiled,
    )


CONTEXT_TILE_ZOOMS = range(11, 17)


@router.get(
    "/context-tiles/{z}/{x}/{y}",
    response={204: None, 403: Error, 409: Error, 422: Error, 503: Error},
    operation_id="previewContextTile",
    openapi_extra={
        "responses": {
            "200": {
                "description": (
                    "Mapbox Vector Tile; layers `building` (`id`)"
                    " and `street` (`id`, `name`, `name_ar`)"
                ),
                "content": {
                    "application/vnd.mapbox-vector-tile": {
                        "schema": {"type": "string", "format": "binary"}
                    }
                },
            }
        }
    },
)
@decorate_view(cached_read)
def context_tile(request, z: int, x: int, y: int, territory: str | None = None):
    from django.http import HttpResponse

    from property_platform.modules.catalog.map_queries import context_tile as read_tile
    from property_platform.modules.publication.coverage import map_source_namespaces

    if z not in CONTEXT_TILE_ZOOMS or not (0 <= x < 2**z and 0 <= y < 2**z):
        return Status(422, {"code": "invalid_query"})
    territory_profile(territory)
    payload = read_tile(z, x, y, namespaces=map_source_namespaces(territory) if territory else None)
    response = HttpResponse(payload, content_type="application/vnd.mapbox-vector-tile")
    if not payload:
        response.status_code = 204
    response["Cache-Control"] = "no-store"
    return response


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
@decorate_view(cached_read)
def parcels(
    request,
    bbox: str,
    limit: int = 3000,
    q: str = "",
    territory: str | None = None,
    after: UUID | None = None,
):
    from property_platform.modules.publication.preview import features

    return _parcel_rows(features, bbox, limit, q, territory, after)


@router.get(
    "/parcel-index",
    response={200: ParcelIndex, 403: Error, 409: Error, 422: Error, 503: Error},
    operation_id="previewParcelIndex",
)
@decorate_view(cached_read)
def parcel_index(
    request,
    bbox: str,
    limit: int = 3000,
    q: str = "",
    territory: str | None = None,
    after: UUID | None = None,
):
    """Parcel rows without footprints; maps draw them from `parcel-tiles`."""
    from property_platform.modules.publication.preview import parcel_index as read_index

    return _parcel_rows(read_index, bbox, limit, q, territory, after)


@router.get(
    "/parcel-search",
    response={200: ParcelIndex, 403: Error, 409: Error, 422: Error, 503: Error},
    operation_id="previewParcelSearch",
)
@decorate_view(cached_read)
def parcel_search(request, q: str, territory: str, limit: int = 12):
    """Index rows whose code starts with `q` anywhere in the territory, so a map
    reading only its visible cells can still find a parcel outside the view."""
    from property_platform.modules.catalog.territories import TERRITORY_BY_ID
    from property_platform.modules.publication.preview import parcel_index as read_index

    query = q.strip()
    if territory not in TERRITORY_BY_ID or not 2 <= len(query) <= 80 or not 1 <= limit <= 50:
        return Status(422, {"code": "invalid_query"})
    profile = territory_profile(territory)
    return read_index(
        bbox=TERRITORY_BY_ID[territory].bounds,
        limit=limit,
        query=query,
        namespaces=profile.parcel_namespaces,
    )


def _parcel_rows(read, bbox, limit, q, territory, after):
    bounds = parse_bbox(bbox)
    query = q.strip()
    if bounds is None or not 1 <= limit <= 3000 or len(query) > 80:
        return Status(422, {"code": "invalid_query"})
    profile = territory_profile(territory)
    if territory and not within_territory(bounds, territory):
        return Status(422, {"code": "invalid_query"})
    return read(
        bbox=bounds,
        limit=limit,
        query=query,
        after=after,
        namespaces=profile.parcel_namespaces if profile else None,
    )


PARCEL_TILE_ZOOMS = range(8, 17)


@router.get(
    "/parcel-tiles/{z}/{x}/{y}",
    response={204: None, 403: Error, 409: Error, 422: Error, 503: Error},
    operation_id="previewParcelTile",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Mapbox Vector Tile; layer `parcels`, property `id` only",
                "content": {
                    "application/vnd.mapbox-vector-tile": {
                        "schema": {"type": "string", "format": "binary"}
                    }
                },
            }
        }
    },
)
@decorate_view(cached_read)
def parcel_tile(request, z: int, x: int, y: int, territory: str | None = None):
    from django.http import HttpResponse

    from property_platform.modules.catalog.queries import parcel_tile as read_tile

    if z not in PARCEL_TILE_ZOOMS or not (0 <= x < 2**z and 0 <= y < 2**z):
        return Status(422, {"code": "invalid_query"})
    profile = territory_profile(territory)
    payload = read_tile(z, x, y, namespaces=profile.parcel_namespaces if profile else None)
    response = HttpResponse(payload, content_type="application/vnd.mapbox-vector-tile")
    if not payload:
        response.status_code = 204
    response["Cache-Control"] = "no-store"
    return response


@router.get(
    "/parcels/{parcel_id}",
    response={200: Detail, 403: Error, 404: Error, 409: Error, 503: Error},
    operation_id="previewParcel",
)
@decorate_view(cached_read)
def parcel(request, parcel_id: UUID, territory: str | None = None):
    profile = territory_profile(territory)
    from property_platform.modules.publication.preview import detail

    result = detail(parcel_id, namespaces=profile.parcel_namespaces if profile else None)
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
    member_territory_ids: tuple[str, ...]
    collection_bounds: tuple[float, float, float, float] | None
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
@decorate_view(cached_read)
def territories(request):
    from property_platform.modules.publication.coverage import coverage_registry

    return coverage_registry()


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
    snapshot_id: UUID
    retrieved_at: datetime
    ingested_at: datetime
    historical: bool


class AdrecSnapshotResponse(Schema):
    id: UUID
    period_start: date
    period_end: date
    ingested_at: datetime
    source_row_count: int


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
    historical: bool
    snapshots: list[AdrecSnapshotResponse]
    rights: SourceRightsResponse | None = None

    @staticmethod
    def resolve_rights(obj):
        return cited_rights(obj, "source_url")


@router.get(
    "/adrec-market",
    response={200: AdrecMarketResponse, 403: Error, 422: Error, 503: Error},
    operation_id="previewAdrecMarket",
)
@decorate_view(cached_read)
def adrec_market(
    request,
    territory: str,
    q: str = "",
    offset: int = 0,
    limit: int = 40,
    snapshot_id: UUID | None = None,
):
    from property_platform.modules.evidence.sources.adrec import DISTRICTS, MAX_ROWS
    from property_platform.modules.publication.adrec_preview import market

    if (
        territory not in DISTRICTS
        or len(q) > 80
        or not 0 <= offset <= MAX_ROWS
        or not 1 <= limit <= 100
    ):
        return Status(422, {"code": "invalid_query"})
    return market(territory, query=q.strip(), offset=offset, limit=limit, snapshot_id=snapshot_id)
