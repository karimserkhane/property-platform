from django.http import HttpResponse
from ninja import Router, Status

from .parcels import Error

router = Router(tags=["local-preview"])


@router.get(
    "/basemap/{provider}/{z}/{x}/{y}",
    response={202: None, 403: Error, 422: Error},
    operation_id="previewBasemapTile",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Archived, source-specific tile bytes",
                "content": {
                    mime: {"schema": {"type": "string", "format": "binary"}}
                    for mime in ("image/png", "application/x-protobuf")
                },
            }
        }
    },
)
def tile(request, provider: str, z: int, x: int, y: int):
    from property_platform.modules.evidence.basemap_archive import archived_tile

    try:
        result = archived_tile(provider, z, x, y)
    except ValueError:
        return Status(422, {"code": "invalid_query"})
    if result is None:
        response = HttpResponse(status=202)
        response["Retry-After"] = "3"
        response["Cache-Control"] = "no-store"
        return response
    row, payload = result
    response = HttpResponse(payload, content_type=row.mime_type)
    response["ETag"] = f'"{row.capture.content_sha256}"'
    response["X-Source-Retrieved-At"] = row.capture.fetched_at.isoformat()
    response["X-Source-Ingested-At"] = row.ingested_at.isoformat()
    response["Cache-Control"] = "public, max-age=86400"
    return response
