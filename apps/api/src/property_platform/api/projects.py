import re
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from django.db import DatabaseError
from ninja import Router, Schema, Status

from .parcels import Error, Geometry, PointGeometry, enabled

router = Router(tags=["local-preview"])


class ProjectSourceResponse(Schema):
    url: str
    name: str
    retrieved_at: datetime
    published_at: datetime | None
    language: str
    evidence_pointer: str = ""
    rights_status: str


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


@router.get(
    "/projects",
    response={200: ProjectDirectoryResponse, 403: Error, 503: Error},
    operation_id="previewProjectDirectory",
)
def projects(request, territory: Literal["al-reem-island", "saadiyat-island"] | None = None):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    from property_platform.modules.evidence.project_queries import project_directory

    try:
        return project_directory(territory)
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})


@router.get(
    "/projects/{slug}",
    response={200: ProjectDetailResponse, 403: Error, 404: Error, 503: Error},
    operation_id="previewProjectDetail",
)
def project_detail(request, slug: str):
    if not enabled():
        return Status(403, {"code": "preview_disabled"})
    if len(slug) > 100 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        return Status(404, {"code": "not_found"})
    from property_platform.modules.evidence.project_queries import project_detail as read_project

    try:
        result = read_project(slug)
        return result if result is not None else Status(404, {"code": "not_found"})
    except DatabaseError:
        return Status(503, {"code": "data_unavailable"})
