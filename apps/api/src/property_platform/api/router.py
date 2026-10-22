from typing import Literal

from django.conf import settings
from django.db import DatabaseError, connection
from ninja import NinjaAPI, Schema, Status

from .accessibility import router as accessibility_router
from .basemaps import router as basemaps_router
from .parcels import router as parcels_router
from .project_media import router as project_media_router
from .projects import router as projects_router
from .public_context import router as context_router

api = NinjaAPI(
    title="Property Platform API",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)
api.add_router("/preview", parcels_router)
api.add_router("/preview", context_router)
api.add_router("/preview", projects_router)
api.add_router("/preview", project_media_router)
api.add_router("/preview", basemaps_router)
api.add_router("/preview", accessibility_router)


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
