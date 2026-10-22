from datetime import date, datetime
from uuid import UUID

from django.db import DatabaseError
from ninja import Router, Schema, Status

from property_platform.modules.publication.coverage import profile_for

from .parcels import Error, enabled

router = Router(tags=["map-analysis-preview"])


class WalkingGeometry(Schema):
    type: str
    coordinates: list[list[list[list[float]]]]


class WalkingProperties(Schema):
    minutes: int
    mode: str


class WalkingFeature(Schema):
    type: str
    geometry: WalkingGeometry
    properties: WalkingProperties


class WalkingCollection(Schema):
    type: str
    features: list[WalkingFeature]


class WalkingResponse(Schema):
    collection: WalkingCollection
    ingested_at: datetime
    graph_id: str
    graph_fetched_at: datetime
    source_url: str
    historical: bool


@router.get(
    "/accessibility",
    response={200: WalkingResponse, 202: Error, 403: Error, 422: Error, 503: Error},
    operation_id="previewWalkingArea",
)
def accessibility(
    request, longitude: float, latitude: float, minutes: int = 10, territory: str = "abu-dhabi"
):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    if profile_for(territory) is None:
        return Status(422, {"code": "invalid_territory"})
    from property_platform.modules.evidence.accessibility import walking_area

    try:
        result = walking_area(longitude, latitude, minutes)
        return result if result is not None else Status(202, {"code": "analysis_pending"})
    except ValueError:
        return Status(422, {"code": "invalid_scope"})
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})


class DistrictMarketProperties(Schema):
    name: str
    name_ar: str
    sales: int
    rate_samples: int
    median_rate: str | None
    volume_aed: str
    boundary_ingested_at: datetime


class DistrictMarketFeature(Schema):
    type: str
    id: str
    geometry: WalkingGeometry
    properties: DistrictMarketProperties


class DistrictMarketResponse(Schema):
    type: str
    features: list[DistrictMarketFeature]
    snapshot_id: UUID | None
    boundary_snapshot_id: UUID | None
    period_start: date | None
    period_end: date | None
    source_url: str
    boundary_source_url: str
    unmatched_sales: int
    mapped_sales: int
    historical: bool


@router.get(
    "/market-map",
    response={200: DistrictMarketResponse, 403: Error, 422: Error, 503: Error},
    operation_id="previewDistrictMarket",
)
def market_map(request, territory: str = "abu-dhabi", q: str = "", snapshot_id: UUID | None = None):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    if profile_for(territory) is None or len(q) > 80:
        return Status(422, {"code": "invalid_scope"})
    from property_platform.modules.publication.market_map import district_market

    try:
        return district_market(territory, query=q.strip(), snapshot_id=snapshot_id)
    except DatabaseError, ValueError:
        return Status(503, {"code": "data_unavailable"})
