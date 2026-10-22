import logging
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.db import OperationalError
from django.test import override_settings

from property_platform.api.preview import preview_only
from property_platform.api.router import api

PREVIEW_PATHS = [
    "parcels?bbox=54.4,24.4,54.5,24.5",
    "parcels/{id}",
    "territories",
    "surroundings/place/{id}",
    "references",
    "imagery",
    "map-context?bbox=54.4,24.4,54.5,24.5",
    "property-media/{id}",
    "adrec-market?territory=al-reem-island",
    "projects",
    "projects/park-view",
    "project-media/{id}",
    "basemap/openfreemap/10/1/1",
    "district-map",
    "public-context?dataset=health",
    "accessibility?longitude=54.4&latitude=24.5",
    "market-map",
]


def test_every_preview_router_is_guarded():
    preview_routers = [router for prefix, router in api._routers if prefix.strip("/") == "preview"]
    assert len(preview_routers) == 6
    for router in preview_routers:
        assert (preview_only, "operation") in router._decorators


@pytest.mark.parametrize("path", PREVIEW_PATHS)
def test_every_preview_route_is_closed_outside_local_preview(client, path):
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=False):
        response = client.get("/api/v1/preview/" + path.format(id=uuid4()))
    assert response.status_code == 403
    assert response.json() == {"code": "preview_disabled"}


def test_database_failures_answer_503_and_keep_details_in_operator_logs(client, caplog):
    with (
        override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True),
        patch(
            "property_platform.modules.publication.coverage.coverage_registry",
            side_effect=OperationalError("private details"),
        ),
        caplog.at_level(logging.ERROR, logger="property_platform.api.router"),
    ):
        response = client.get("/api/v1/preview/territories")
    assert response.status_code == 503
    assert response.json() == {"code": "data_unavailable"}
    assert "private details" not in response.content.decode()
    [record] = [r for r in caplog.records if r.name == "property_platform.api.router"]
    assert record.exc_info[0] is OperationalError
    assert "/api/v1/preview/territories" in record.getMessage()
