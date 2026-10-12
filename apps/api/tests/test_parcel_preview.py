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
        for path in (
            "territories",
            "references",
            "imagery",
            "map-context?bbox=54.4,24.4,54.5,24.5",
        ):
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


@pytest.mark.parametrize("territory", ["dubai", "uae", "unknown-area"])
@pytest.mark.parametrize(
    "path", ["parcels", "map-context", "references", "imagery", "parcels/{id}"]
)
def test_unconfigured_territory_never_falls_back_to_pilot_or_accesses_gis(client, territory, path):
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get(
            "/api/v1/preview/" + path.format(id=uuid4()),
            {"territory": territory, "bbox": "55.1,25.1,55.2,25.2"},
        )
    assert response.status_code == 409
    assert response.json()["code"] == "territory_not_configured"


@pytest.mark.parametrize("path", ["parcels", "map-context"])
def test_scoped_query_outside_pilot_is_rejected_before_accessing_gis(client, path):
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get(
            "/api/v1/preview/" + path,
            {"territory": "al-reem-island", "bbox": "55.1,25.1,55.2,25.2"},
        )
    assert response.status_code == 422
