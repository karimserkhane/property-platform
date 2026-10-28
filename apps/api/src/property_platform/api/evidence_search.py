from datetime import datetime
from functools import wraps
from typing import Literal

from ninja import Query, Router, Schema
from ninja.decorators import decorate_view

from .parcels import Error
from .read_cache import cached_read


def _cached_text_read(run):
    """Cache full-text answers only.

    A hybrid answer depends on the optional embeddings service, not only on the data the
    read cache tracks: a fallback stored while the service was down would outlive it.
    """
    cached = cached_read(run)

    @wraps(run)
    def read(request, *args, **kwargs):
        if request.GET.get("mode", "text") == "text":
            return cached(request, *args, **kwargs)
        return run(request, *args, **kwargs)

    return read


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
    mode: Literal["text", "hybrid"]
    # True only when a hybrid answer includes the optional semantic ranking.
    semantic: bool


@router.get(
    "/evidence-search",
    response={200: EvidenceSearchResponse, 403: Error, 503: Error},
    operation_id="previewEvidenceSearch",
)
@decorate_view(_cached_text_read)
def evidence_search(
    request,
    q: str = Query(..., min_length=1, max_length=120),
    territory: Literal["al-reem-island", "saadiyat-island", "al-maryah-island"] | None = None,
    limit: int = Query(20, ge=1, le=50),
    mode: Literal["text", "hybrid"] = "text",
):
    """Published statements matching `q`, each with its evidence (E01).

    `text` requires every word; `hybrid` fuses it with the optional semantic ranking and
    answers with the full text alone without the embeddings service.
    """
    from property_platform.modules.evidence.search.index import hybrid_claims, search_claims

    if mode == "hybrid":
        items, semantic = hybrid_claims(q, territory=territory, limit=limit)
    else:
        items, semantic = search_claims(q, territory=territory, limit=limit), False
    return {"items": items, "mode": mode, "semantic": semantic}
