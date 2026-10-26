from datetime import datetime
from typing import Literal

from ninja import Query, Router, Schema
from ninja.decorators import decorate_view

from .parcels import Error
from .read_cache import cached_read

router = Router(tags=["local-preview"])


class EvidenceSearchProjectResponse(Schema):
    slug: str
    name: str


class EvidenceSearchSourceResponse(Schema):
    url: str
    name: str
    kind: str
    content_sha256: str | None
    evidence_pointer: str
    retrieved_at: datetime | None


class EvidenceSearchClaimResponse(Schema):
    claim_key: str
    project: EvidenceSearchProjectResponse
    kind: Literal[
        "summary",
        "handover",
        "programme_total",
        "typologies",
        "amenity",
        "declared_progress",
        "registration",
        "component_of",
        "has_component",
    ]
    path: str
    text: str
    language: str
    source: EvidenceSearchSourceResponse
    indexed_at: datetime


class EvidenceSearchResponse(Schema):
    items: list[EvidenceSearchClaimResponse]


@router.get(
    "/evidence-search",
    response={200: EvidenceSearchResponse, 403: Error, 503: Error},
    operation_id="previewEvidenceSearch",
)
@decorate_view(cached_read)
def evidence_search(
    request,
    q: str = Query(..., min_length=1, max_length=120),
    territory: Literal["al-reem-island", "saadiyat-island", "al-maryah-island"] | None = None,
    limit: int = Query(20, ge=1, le=50),
):
    """Published statements matching every word of `q`, each with its evidence (E01)."""
    from property_platform.modules.evidence.search.index import search_claims

    return {"items": search_claims(q, territory=territory, limit=limit)}
