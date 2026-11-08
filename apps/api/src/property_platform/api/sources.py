from datetime import date, datetime
from typing import Literal

from ninja import Router, Schema
from ninja.decorators import decorate_view

from .parcels import Error
from .read_cache import cached_read

router = Router(tags=["local-preview"])


class SourceSiteRightsResponse(Schema):
    """One reviewed site of the source rights registry (A19); `unknown` means not qualified."""

    host: str
    publisher: str
    licence: str
    licence_url: str | None = None
    terms_url: str | None = None
    collection: Literal["allowed", "forbidden"]
    publication: Literal["open", "facts", "link", "none"]
    attribution: str | None = None
    reviewed_on: date | None = None


class SourceRightsRegistryResponse(Schema):
    items: list[SourceSiteRightsResponse]


@router.get(
    "/source-rights",
    response={200: SourceRightsRegistryResponse, 403: Error},
    operation_id="previewSourceRights",
)
def source_rights(request):
    from property_platform.modules.evidence.source_rights import source_rights as registry

    return {
        "items": [
            row
            | {
                "licence_url": row["licence_url"] or None,
                "terms_url": row["terms_url"] or None,
                "attribution": row["attribution"] or None,
            }
            for row in registry()
        ]
    }


class SourceFamilyFreshnessResponse(Schema):
    """Latest success of one family and the moments it becomes late, then to be reviewed.

    The reader compares these with its own clock (A32), so the state of a family never
    goes stale in the read cache while no run is written.
    """

    family: str
    cadence_days: int
    last_success_at: datetime | None = None
    late_from: datetime | None = None
    review_from: datetime | None = None
    sources_total: int
    sources_behind: int


class FailingDeploymentResponse(Schema):
    deployment: str
    failures: int
    last_failed_at: datetime


class LateQueueResponse(Schema):
    deployment: str
    runs: int
    oldest_expected_at: datetime


class OperationsReportResponse(Schema):
    generated_at: datetime
    failing_deployments: list[FailingDeploymentResponse]
    late_queues: list[LateQueueResponse]


class SourceFreshnessResponse(Schema):
    families: list[SourceFamilyFreshnessResponse]
    operations: OperationsReportResponse | None = None


@router.get(
    "/source-freshness",
    response={200: SourceFreshnessResponse, 403: Error},
    operation_id="previewSourceFreshness",
)
@decorate_view(cached_read)
def source_freshness(request):
    from property_platform.modules.evidence.history.source_freshness import (
        family_freshness,
        latest_report,
    )

    return {"families": family_freshness(), "operations": latest_report()}
