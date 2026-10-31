import re
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from ninja import Query, Router, Schema, Status
from ninja.decorators import decorate_view

from .parcels import Error, Geometry, PointGeometry, SourceRightsResponse, cited_rights
from .read_cache import cached_read

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
    rights: SourceRightsResponse | None = None
    ingested_at: datetime | None = None
    historical: bool = False

    @staticmethod
    def resolve_rights(obj):
        # Every cited project source states its rights, whichever read built it (A24).
        rights = obj.get("rights") if isinstance(obj, dict) else getattr(obj, "rights", None)
        return rights or cited_rights(obj, "url")


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
    # The page the file was found on; the file's own licence is `licence_code` (A24).
    rights: SourceRightsResponse | None = None

    @staticmethod
    def resolve_rights(obj):
        return cited_rights(obj, "source_url")


class ProjectMapLocationResponse(Schema):
    id: UUID
    target: Literal["building", "place", "parcel"]
    method: Literal[
        "cadastral_parcel",
        "building_footprint",
        "authority_point",
        "broker_point",
        "publisher_point",
        "declared_point",
    ]
    precision: Literal["boundary", "footprint", "point"]
    name: str
    geometry: Geometry | PointGeometry
    source: ProjectSourceResponse


class ProjectRelationResponse(Schema):
    """The other project of a reviewed component link, never a merged identity."""

    slug: str
    name: str
    component: str
    basis: str
    source_url: str
    retrieved_at: datetime
    rights: SourceRightsResponse | None = None


class ProjectDeclaredProgressResponse(Schema):
    """Latest completion the authority register declares, dated by its inspection."""

    authority: Literal["adrec"]
    progress_percent: float
    progress_inspected_on: date | None
    register_status: str
    off_plan: bool | None
    source: ProjectSourceResponse


class RetentionBandResponse(Schema):
    lower_percent: float
    upper_percent: float


class RetentionReferenceResponse(Schema):
    publisher: str
    published_on: date
    url: str
    consulted_on: date
    covers: str
    rights: SourceRightsResponse | None = None


class RetentionSourceResponse(Schema):
    decision: str
    official_text_obtained: bool
    references: list[RetentionReferenceResponse]


class CancellationRetentionResponse(Schema):
    """Developer retention on cancellation at the declared stage; a reading aid, not advice."""

    version: str
    status: Literal["rate", "boundary", "unknown", "out_of_range"]
    progress_percent: float | None
    progress_inspected_on: date | None
    rates: list[int]
    bands: list[RetentionBandResponse]
    full_refund_possible: bool
    paid_share_discretion_percent: int
    source: RetentionSourceResponse
    progress_source: ProjectSourceResponse


class DeliveryOutcomeResponse(Schema):
    """Whether a register reading proves the announced period was met or missed."""

    status: Literal["met", "late", "undetermined"]
    late_by_at_least_days: int | None
    source: ProjectSourceResponse | None


class DeliveryAnnouncementResponse(Schema):
    precision: Literal["year", "quarter", "month", "day"]
    year: int
    quarter: int | None
    month: int | None
    day: int | None
    original_text: str
    window_start: date
    window_end: date
    first_observed_at: datetime
    last_observed_at: datetime
    readings: int
    change: Literal["first", "later", "earlier", "refined"]
    outcome: DeliveryOutcomeResponse
    source: ProjectSourceResponse


class DeliveryRegisterResponse(Schema):
    status: str
    completed: bool
    progress_percent: float | None
    progress_inspected_on: date | None
    first_observed_at: datetime
    last_observed_at: datetime
    readings: int
    source: ProjectSourceResponse


class DeliveryCompletionResponse(Schema):
    observed_at: datetime
    not_completed_until: datetime | None
    source: ProjectSourceResponse


class VerificationRegisterResponse(Schema):
    """Latest project-scope register reading, values as published."""

    authority: Literal["adrec"]
    registration_number: str
    permit_number: str | None
    register_status: str | None
    off_plan: bool | None
    registered_on: date | None
    progress_percent: float | None
    progress_inspected_on: date | None
    inspection_company: str | None
    progress_report_url: str | None
    progress_report_valid_until: date | None
    progress_report_expired: bool | None
    sold_percent: float | None
    sold_original: str | None
    escrow_bank_name: str | None
    escrow_account_number: str | None
    developer_licence: str | None
    observed_at: datetime
    source: ProjectSourceResponse


class VerificationLinkResponse(Schema):
    """Official register page an operator matched to the project; never read by the platform."""

    authority: Literal["adrec"]
    registration_number: str
    url: str
    reviewed_on: date
    rights: SourceRightsResponse | None = None


class VerificationContradictionResponse(Schema):
    """Two cited readings that disagree; no cause is inferred."""

    code: Literal[
        "announced_after_completion",
        "announced_period_passed",
        "sources_disagree",
        "progress_decreased",
    ]
    late_by_at_least_days: int | None
    announcements: list[DeliveryAnnouncementResponse]
    register_readings: list[DeliveryRegisterResponse]


class ProjectVerificationResponse(Schema):
    latest_reading: VerificationRegisterResponse | None
    register_readings: list[DeliveryRegisterResponse]
    completion: DeliveryCompletionResponse | None
    official_links: list[VerificationLinkResponse]
    contradictions: list[VerificationContradictionResponse]


class ActivityWindowResponse(Schema):
    """Captured Sentinel-2 file window that one date of a measurement was computed from."""

    url: str
    content_sha256: str


class ActivityMeasurementResponse(Schema):
    """Ground change between two scenes of a parcel; a signal, never a progress share."""

    status: Literal["measured", "insufficient_clear_pixels"]
    level: Literal["low", "moderate", "high"] | None
    method_version: str
    tile: str
    before_scene_id: str
    after_scene_id: str
    before_acquired_at: datetime
    after_acquired_at: datetime
    parcel_pixels: int
    clear_pixels: int
    measured_at: datetime
    before_window: ActivityWindowResponse
    after_window: ActivityWindowResponse


class ActivityParcelResponse(Schema):
    source_namespace: str
    source_record_id: str
    official_plot_id: str | None
    area_m2: int
    area_basis: Literal["reviewed_parcel", "parcel_containing_position"]
    position_method: Literal["cadastral_parcel", "authority_point", "building_footprint"]
    latest: ActivityMeasurementResponse


class ActivitySourceResponse(Schema):
    name: str
    url: str
    rights: SourceRightsResponse | None = None


class ProjectConstructionActivityResponse(Schema):
    """Latest satellite measurement of each measured parcel of the project."""

    source: ActivitySourceResponse
    parcels: list[ActivityParcelResponse]


class ObservedSalesLabelResponse(Schema):
    """Reviewed ADREC sales label that selects the project's recorded sales."""

    district: str
    label: str
    evidence: Literal["register_name", "project_name"]
    registration_number: str | None
    reviewed_on: date


class ObservedSalesCaptureResponse(Schema):
    url: str
    content_sha256: str


class ObservedSalesWindowResponse(Schema):
    """Newest ADREC sales window of the territory; windows overlap and are never added."""

    territory: str
    period_start: date
    period_end: date
    collected_at: datetime
    captures: list[ObservedSalesCaptureResponse]


class ObservedRangeResponse(Schema):
    """Smallest and largest recorded value, as decimal text."""

    min: str
    max: str


class ObservedSalesGroupResponse(Schema):
    """Recorded sales of one type; ranges cover the full-share sales only."""

    property_type: str
    property_layout: str
    sale_application_type: str
    sale_sequence: str
    sales_count: int
    full_share_count: int
    price_aed: ObservedRangeResponse | None
    rate_aed_per_sqm: ObservedRangeResponse | None
    sold_area_sqm: ObservedRangeResponse | None
    first_registration_date: date
    last_registration_date: date


class ProjectObservedSalesResponse(Schema):
    """Recorded ADREC sales of the project's reviewed labels, by type, with ranges."""

    source: ActivitySourceResponse
    labels: list[ObservedSalesLabelResponse]
    window: ObservedSalesWindowResponse | None
    groups: list[ObservedSalesGroupResponse]


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
    parent: ProjectRelationResponse | None = None
    components: list[ProjectRelationResponse] = []
    declared_progress: ProjectDeclaredProgressResponse | None = None
    cancellation_retention: CancellationRetentionResponse | None = None
    verification: ProjectVerificationResponse | None = None
    construction_activity: ProjectConstructionActivityResponse | None = None
    observed_sales: ProjectObservedSalesResponse | None = None


class ProjectSummaryResponse(Schema):
    id: UUID
    slug: str
    name: str
    territory: str
    developer: ProjectDeveloperResponse
    website_url: str
    updated_at: datetime
    has_map_identity: bool
    parent: ProjectRelationResponse | None = None
    component_count: int = 0


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
@decorate_view(cached_read)
def projects(
    request,
    territory: Literal["al-reem-island", "saadiyat-island", "al-maryah-island"] | None = None,
    q: str = Query("", max_length=120),
    offset: int = Query(0, ge=0, le=50000),
    limit: int = Query(200, ge=1, le=200),
):
    from property_platform.modules.evidence.projects.project_queries import project_directory

    return project_directory(territory, query=q, offset=offset, limit=limit)


@router.get(
    "/projects/{slug}",
    response={200: ProjectDetailResponse, 403: Error, 404: Error, 503: Error},
    operation_id="previewProjectDetail",
)
@decorate_view(cached_read)
def project_detail(request, slug: str):
    if len(slug) > 100 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        return Status(404, {"code": "not_found"})
    from property_platform.modules.evidence.projects.project_queries import (
        project_detail as read_project,
    )
    from property_platform.modules.publication.cancellation_retention import project_retention

    result = read_project(slug)
    if result is None:
        return Status(404, {"code": "not_found"})
    return result | {"cancellation_retention": project_retention(result["declared_progress"])}


class DeliveryProjectResponse(Schema):
    slug: str
    name: str
    territory: str
    announcements: list[DeliveryAnnouncementResponse]
    register_readings: list[DeliveryRegisterResponse]
    completion: DeliveryCompletionResponse | None


class DeliverySummaryResponse(Schema):
    projects: int
    with_announcements: int
    with_register: int
    completed_observed: int
    late_observed: int
    announcement_moved_later: int


class DeveloperDeliveryHistoryResponse(Schema):
    developer: ProjectDeveloperResponse
    summary: DeliverySummaryResponse
    projects: list[DeliveryProjectResponse]


@router.get(
    "/developers/{key}/delivery-history",
    response={200: DeveloperDeliveryHistoryResponse, 403: Error, 404: Error, 503: Error},
    operation_id="previewDeveloperDeliveryHistory",
)
@decorate_view(cached_read)
def developer_delivery_history(request, key: str):
    if len(key) > 100 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key):
        return Status(404, {"code": "not_found"})
    from property_platform.modules.evidence.projects.delivery_history import (
        developer_delivery_history as read_history,
    )

    result = read_history(key)
    return result if result is not None else Status(404, {"code": "not_found"})
