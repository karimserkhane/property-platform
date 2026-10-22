"""Approved private project files, streamed with single HTTP byte-range support."""

from uuid import UUID

from django.http import HttpResponse, StreamingHttpResponse
from ninja import Router, Status

from property_platform.object_storage.core import MIME_TYPES, StorageError
from property_platform.object_storage.downloads import (
    UnsatisfiableRange,
    describe_object,
    download_range,
    open_object,
)

from .parcels import Error

router = Router(tags=["local-preview"])
RESPONSES = {200: None, 206: None, 403: Error, 404: Error, 416: None, 503: Error}


def _download(request, media_id):
    from property_platform.modules.evidence.media_storage import receipt_store
    from property_platform.modules.evidence.project_media_storage import authorized_asset

    try:
        asset = authorized_asset(media_id)
        if asset is None:
            return Status(404, {"code": "not_found"})
        media, receipt = asset
        store = receipt_store(receipt)
        etag = f'"{receipt.sha256}"'
        value = request.headers.get("Range") if request.method == "GET" else None
        if request.headers.get("If-Range", etag) != etag:
            value = None
        try:
            span = download_range(value, receipt.size)
        except UnsatisfiableRange:
            return HttpResponse(
                status=416,
                headers={
                    "Content-Range": f"bytes */{receipt.size}",
                    "Cache-Control": "no-store",
                    "Accept-Ranges": "bytes",
                    "ETag": etag,
                },
            )
        headers = {
            "Content-Type": receipt.mime_type,
            "Content-Length": str(span.size),
            "Accept-Ranges": "bytes",
            "ETag": etag,
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": ("inline" if media.kind in {"image", "video"} else "attachment")
            + f'; filename="{media.id}.{MIME_TYPES[receipt.mime_type]}"',
        }
        if span.partial:
            headers["Content-Range"] = f"bytes {span.start}-{span.end}/{receipt.size}"
        if request.method == "HEAD":
            describe_object(store, receipt)
            return HttpResponse(headers=headers)
        download = open_object(store, receipt, span)
        return StreamingHttpResponse(download, status=206 if span.partial else 200, headers=headers)
    except StorageError:
        return Status(503, {"code": "data_unavailable"})


@router.get("/project-media/{media_id}", response=RESPONSES, operation_id="previewProjectMedia")
def project_media(request, media_id: UUID):
    return _download(request, media_id)


@router.api_operation(
    ["HEAD"],
    "/project-media/{media_id}",
    response=RESPONSES,
    operation_id="previewProjectMediaHead",
)
def project_media_head(request, media_id: UUID):
    return _download(request, media_id)
