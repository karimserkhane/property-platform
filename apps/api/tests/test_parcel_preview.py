from uuid import uuid4

import pytest
from django.test import override_settings


def test_preview_is_disabled_even_with_flag_in_non_debug_mode(client):
    with override_settings(DEBUG=False, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        assert (
            client.get("/api/v1/preview/parcels", {"bbox": "54.4,24.4,54.5,24.5"}).status_code
            == 403
        )
        assert client.get(f"/api/v1/preview/parcels/{uuid4()}").status_code == 403
        for path in ("references", "imagery", "map-context?bbox=54.4,24.4,54.5,24.5"):
            assert client.get(f"/api/v1/preview/{path}").status_code == 403


@pytest.mark.parametrize(
    "query",
    [
        {"bbox": "nan,24,54,25"},
        {"bbox": "-180,-90,180,90"},
        {"bbox": "54.4,24.5,54.3,24.6"},
        {"bbox": "54.4,24.5,54.5"},
        {"bbox": "54.4,24.5,54.5,24.6", "limit": "3001"},
        {"bbox": "54.4,24.5,54.5,24.6", "limit": "0"},
        {"bbox": "54.4,24.5,54.5,24.6", "q": "x" * 81},
    ],
)
def test_invalid_queries_are_rejected_before_accessing_gis(client, query):
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get("/api/v1/preview/parcels", query)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_query"
