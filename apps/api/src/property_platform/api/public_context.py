"""Local preview delivery; public redistribution rights remain a separate review."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from ninja import Router, Schema, Status

from property_platform.modules.publication.coverage import profile_for

from .parcels import Error

router = Router(tags=["public-context-preview"])


class HistoricalField(Schema):
    retrieved_at: datetime
    ingested_at: datetime


class ContextRow(Schema):
    source_record_id: str
    name: str
    snapshot_id: UUID
    retrieved_at: datetime
    ingested_at: datetime
    historical: bool
    field_history: dict[str, HistoricalField]


class FacilityResponse(ContextRow):
    facility_type: str
    address: str
    planned: bool
    operator: str
    licence_number: str
    services_original: str
    longitude: float
    latitude: float


class SchoolResponse(ContextRow):
    name_ar: str
    municipality: str
    district: str
    district_ar: str
    community: str
    grades_original: str
    longitude: float
    latitude: float


class BusRouteResponse(ContextRow):
    number: str
    origin: str
    destination: str
    timetable_url: str


class DistrictResponse(ContextRow):
    name_ar: str
    municipality: str
    district_id: int
    bounds: tuple[float, float, float, float]


class CensusResponse(ContextRow):
    reference_year: int
    region: str
    category: str
    unit: str
    value: str
    rounding_base: int | None


class PublicContextResponse(Schema):
    dataset: str
    territory: str
    snapshot_id: UUID | None
    retrieved_at: datetime | None
    acquisition_method: str | None
    timestamp_basis: str | None
    source_modified_date: date | None
    source_url: str
    reuse_status: str
    total: int
    offset: int
    has_more: bool
    health: list[FacilityResponse]
    districts: list[DistrictResponse]
    schools: list[SchoolResponse]
    mobility: list[BusRouteResponse]
    statistics: list[CensusResponse]


class DistrictMapProperties(DistrictResponse):
    label_point: tuple[float, float]
    explore_territory_id: str | None


class DistrictMapGeometry(Schema):
    type: Literal["MultiPolygon"]
    coordinates: list[list[list[list[float]]]]


class DistrictMapFeature(Schema):
    type: Literal["Feature"]
    id: str
    geometry: DistrictMapGeometry
    properties: DistrictMapProperties


class DistrictMapResponse(Schema):
    type: Literal["FeatureCollection"]
    territory: Literal["abu-dhabi"]
    snapshot_id: UUID | None
    retrieved_at: datetime | None
    source_url: str
    display_geometry_version: str
    features: list[DistrictMapFeature]


@router.get(
    "/district-map",
    response={200: DistrictMapResponse, 403: Error, 503: Error},
    operation_id="previewDistrictMap",
)
def districts(request):
    from property_platform.modules.publication.context_preview import district_map

    try:
        return district_map()
    except ValueError:
        return Status(503, {"code": "data_unavailable"})


@router.get(
    "/public-context",
    response={200: PublicContextResponse, 403: Error, 422: Error, 503: Error},
    operation_id="previewPublicContext",
)
def context(
    request,
    dataset: Literal["health", "schools", "mobility", "statistics", "districts"],
    territory: str = "abu-dhabi",
    q: str = "",
    offset: int = 0,
    limit: int = 40,
):
    if (
        profile_for(territory) is None
        or len(q) > 80
        or not 0 <= offset <= 5000
        or not 1 <= limit <= 100
    ):
        return Status(422, {"code": "invalid_query"})
    from property_platform.modules.publication.context_preview import public_context

    return public_context(dataset, query=q.strip(), offset=offset, limit=limit)
