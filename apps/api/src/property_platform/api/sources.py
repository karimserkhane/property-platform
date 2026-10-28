from datetime import date
from typing import Literal

from ninja import Router, Schema

from .parcels import Error

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
