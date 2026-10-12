import os
from uuid import uuid4

import pytest
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Preview integration requires real PostGIS", allow_module_level=True)

from test_onwani_postgis import feature, run  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def test_preview_geometry_filter_provenance_and_private_field_allowlist(client):
    run([feature(1, "RT1_C1"), feature(2, "RT1_C2")])
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get(
            "/api/v1/preview/parcels", {"bbox": "54.39,24.49,54.42,24.52", "limit": 1}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["truncated"] is True
        assert len(data["features"]) == 1
        item = data["features"][0]
        assert item["geometry"]["type"] == "MultiPolygon"
        assert set(item["properties"]) == {
            "id",
            "code",
            "community",
            "land_use",
            "construction_status",
            "category",
        }
        detail = client.get(f"/api/v1/preview/parcels/{item['id']}")
        assert detail.status_code == 200
        assert detail.json()["source"]["published_at"] is None
        assert detail.json()["source"]["retrieved_at"]
        for private in ["raw_attributes", "actor", "payload", "record_sha256"]:
            assert private not in detail.json()
        assert client.get(f"/api/v1/preview/parcels/{uuid4()}").status_code == 404
        outside = client.get("/api/v1/preview/parcels", {"bbox": "54.1,24.1,54.2,24.2"})
        assert outside.json()["features"] == []
        searched = client.get(
            "/api/v1/preview/parcels", {"bbox": "54.39,24.49,54.42,24.52", "q": "rt1_c2"}
        )
        assert len(searched.json()["features"]) == 1
        assert searched.json()["features"][0]["properties"]["code"] == "RT1_C2"
