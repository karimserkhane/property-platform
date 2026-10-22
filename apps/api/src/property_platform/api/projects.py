import re
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from ninja import Query, Router, Schema, Status

from .parcels import Error, Geometry, PointGeometry

router = Router(tags=["local-preview"])


class ProjectSourceResponse(Schema):
    url: str
    name: str
    kind: Literal[
        "developer", "publisher", "broker", "authority", "media", "community", "reference"
    ] = "developer"
    content_sha256: str | None = None
    developer_name: str | None = None
    developer_role: Literal["declared", "registered"] | None = None
    retrieved_at: datetime
    published_at: datetime | None
    language: str
    evidence_pointer: str = ""
    rights_status: str
    ingested_at: datetime | None = None
    historical: bool = False


class ProjectDeveloperResponse(Schema):
    id: UUID
    key: str
    name: str
    website_url: str


class ProjectHandoverResponse(Schema):
    precision: Literal["year", "quarter", "month", "day"]
    year: int
    quarter: int | None
    month: int | None
    day: int | None
    original_text: str
    source: ProjectSourceResponse


class ProjectTypologyResponse(Schema):
    property_type: str
    bedrooms: int | None
    original_text: str
    source: ProjectSourceResponse


class ProjectAmenityResponse(Schema):
    code: str
    label: str
    original_text: str
    source: ProjectSourceResponse


class ProjectProgrammeResponse(Schema):
    value: int
    basis: Literal["announced", "registered"] = "announced"
    original_text: str
    source: ProjectSourceResponse


class ProjectMediaResponse(Schema):
    id: UUID
    kind: Literal["image", "document", "video", "model"]
    role: str
    title: str
    mime_type: str
    source_url: str
    original_text: str
    rights_status: Literal["reference_only", "approved", "blocked"]
    delivery_url: str | None
    author: str | None = None
    licence_code: str | None = None
    licence_url: str | None = None
    taken_on: date | None = None
    duration_seconds: int | None = None
    width: int | None = None
    height: int | None = None
    source: ProjectSourceResponse


class ProjectMapLocationResponse(Schema):
    id: UUID
    target: Literal["building", "place", "parcel"]
    name: str
    geometry: Geometry | PointGeometry
    source: ProjectSourceResponse


class ProjectDetailResponse(Schema):
    id: UUID
    slug: str
    name: str
    territory: str
    developer: ProjectDeveloperResponse
    website_url: str
    summary: str
    summary_source: ProjectSourceResponse | None = None
    language: str
    updated_at: datetime
    handover: ProjectHandoverResponse | None
    programme_total: ProjectProgrammeResponse | None
    typologies: list[ProjectTypologyResponse]
    amenities: list[ProjectAmenityResponse]
    media: list[ProjectMediaResponse]
    sources: list[ProjectSourceResponse]
    map_locations: list[ProjectMapLocationResponse]


class ProjectSummaryResponse(Schema):
    id: UUID
    slug: str
    name: str
    territory: str
    developer: ProjectDeveloperResponse
    website_url: str
    updated_at: datetime
    has_map_identity: bool


class ProjectDirectoryResponse(Schema):
    items: list[ProjectSummaryResponse]
    has_more: bool
    total: int
    offset: int


@router.get(
    "/projects",
    response={200: ProjectDirectoryResponse, 403: Error, 503: Error},
    operation_id="previewProjectDirectory",
)
def projects(
    request,
    territory: Literal["al-reem-island", "saadiyat-island", "al-maryah-island"] | None = None,
    q: str = Query("", max_length=120),
    offset: int = Query(0, ge=0, le=50000),
    limit: int = Query(200, ge=1, le=200),
):
    from property_platform.modules.evidence.project_queries import project_directory

    return project_directory(territory, query=q, offset=offset, limit=limit)


@router.get(
    "/projects/{slug}",
    response={200: ProjectDetailResponse, 403: Error, 404: Error, 503: Error},
    operation_id="previewProjectDetail",
)
def project_detail(request, slug: str):
    if len(slug) > 100 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        return Status(404, {"code": "not_found"})
    from property_platform.modules.evidence.project_queries import project_detail as read_project

    result = read_project(slug)
    return result if result is not None else Status(404, {"code": "not_found"})
