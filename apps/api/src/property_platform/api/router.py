import logging
from typing import Literal

from django.conf import settings
from django.db import DatabaseError, connection
from ninja import NinjaAPI, Schema, Status

from .accessibility import router as accessibility_router
from .basemaps import router as basemaps_router
from .parcels import router as parcels_router
from .preview import TerritoryNotConfigured, preview_only
from .project_media import router as project_media_router
from .projects import router as projects_router
from .public_context import router as context_router

logger = logging.getLogger(__name__)

api = NinjaAPI(
    title="Property Platform API",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)
for preview_router in (
    parcels_router,
    context_router,
    projects_router,
    project_media_router,
    basemaps_router,
    accessibility_router,
):
    preview_router.add_decorator(preview_only)
    api.add_router("/preview", preview_router)


@api.exception_handler(DatabaseError)
def data_unavailable(request, exc):
    # Readiness keeps its own answer; every other route reports a failed read as 503.
    logger.error("Database read failed: %s %s", request.method, request.path, exc_info=exc)
    return api.create_response(request, {"code": "data_unavailable"}, status=503)


@api.exception_handler(TerritoryNotConfigured)
def territory_not_configured(request, exc):
    return api.create_response(request, {"code": "territory_not_configured"}, status=409)


class Health(Schema):
    status: Literal["ok", "ready", "unavailable"]


@api.get("/health/live", response=Health, operation_id="healthLive", tags=["health"])
def live(request):
    return {"status": "ok"}


@api.get(
    "/health/ready",
    response={200: Health, 503: Health},
    operation_id="healthReady",
    tags=["health"],
)
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT PostGIS_Version()")
            if not cursor.fetchone():
                return Status(503, {"status": "unavailable"})
    except DatabaseError:
        return Status(503, {"status": "unavailable"})
    return Status(200, {"status": "ready"})
