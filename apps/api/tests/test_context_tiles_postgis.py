import math
import os

import pytest
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Context tiles require real PostGIS", allow_module_level=True)

from test_reem_map_postgis import collect, district, osm  # noqa: E402

from property_platform.modules.catalog.models import Building, Street  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

PREVIEW = {"DEBUG": True, "PROPERTY_PLATFORM_PARCEL_PREVIEW": True}
BBOX = {"bbox": "54.39,24.49,54.42,24.52"}


def tile_path(lon, lat, z):
    n = 2**z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return f"/api/v1/preview/context-tiles/{z}/{x}/{y}"


def with_street():
    data = osm()
    data["elements"].append(
        {
            "type": "way",
            "id": 3,
            "timestamp": "2026-01-01T00:00:00Z",
            "version": 1,
            "tags": {"highway": "residential", "name": "Real source street"},
            "geometry": [{"lon": 54.398, "lat": 24.5005}, {"lon": 54.403, "lat": 24.5005}],
        }
    )
    return data


def test_tiles_draw_active_buildings_and_streets_by_identity(client):
    district()
    collect(with_street())
    building, street = Building.objects.get(), Street.objects.get()
    with override_settings(**PREVIEW):
        response = client.get(tile_path(54.4005, 24.5005, 15))
        assert response.status_code == 200
        assert response["Content-Type"] == "application/vnd.mapbox-vector-tile"
        payload = response.content
        assert b"building" in payload and str(building.pk).encode() in payload
        assert b"street" in payload and str(street.pk).encode() in payload
        # Street names label lines; building names, heights and sources stay in the index.
        assert b"Real source street" in payload
        assert b"Real source building" not in payload and b"apartments" not in payload
        assert client.get(tile_path(54.1, 24.1, 15)).status_code == 204
        Building.objects.update(active=False)
        Street.objects.update(active=False)
        assert client.get(tile_path(54.4005, 24.5005, 15)).status_code == 204


def test_overview_tiles_leave_out_sub_pixel_buildings(client):
    district()
    collect(osm())
    building = Building.objects.get()
    with override_settings(**PREVIEW):
        # About 100 m wide: wider than half a pixel at zoom 11, the smallest served;
        # about 2 m wide afterwards.
        assert str(building.pk).encode() in client.get(tile_path(54.4005, 24.5005, 11)).content
        corner = ((54.4, 24.5), (54.40002, 24.5), (54.40002, 24.50002), (54.4, 24.5))
        shrunk = MultiPolygon(Polygon(corner), srid=4326)
        Building.objects.update(geometry=shrunk)
        assert client.get(tile_path(54.4005, 24.5005, 11)).status_code == 204
        # From the detail zoom every building is drawn, once it spans tile units.
        assert client.get(tile_path(54.40001, 24.50001, 16)).status_code == 200


@pytest.mark.parametrize(
    "path", ["10/683/440", "17/86000/56000", "14/-1/7041", "14/16384/7041", "14/10668/16384"]
)
def test_tiles_reject_unserved_zooms_and_coordinates(client, path):
    with override_settings(**PREVIEW):
        response = client.get(f"/api/v1/preview/context-tiles/{path}")
    assert response.status_code in {404, 422}


def test_tiles_respect_territory_scope(client):
    district()
    collect(with_street())
    with override_settings(**PREVIEW):
        path = tile_path(54.4005, 24.5005, 15)
        assert client.get(path, {"territory": "dubai"}).status_code == 409
        scoped = client.get(path, {"territory": "al-reem-island"})
        assert scoped.status_code == 200
        assert str(Building.objects.get().pk).encode() in scoped.content


def test_index_matches_map_context_without_tiled_geometry(client):
    district()
    collect(with_street())
    with override_settings(**PREVIEW):
        full = client.get("/api/v1/preview/map-context", BBOX).json()
        index = client.get("/api/v1/preview/context-index", BBOX).json()
    assert index["place"] == full["place"]
    assert index["administrative_area"] == full["administrative_area"]
    for family in ("building", "street"):
        assert index[family]["truncated"] == full[family]["truncated"]
        assert [row["id"] for row in index[family]["features"]] == [
            row["id"] for row in full[family]["features"]
        ]
        assert index[family]["features"]
        for row, published in zip(index[family]["features"], full[family]["features"], strict=True):
            assert "geometry" not in row
            properties = dict(row["properties"])
            west, south, east, north = properties.pop("bounds")
            assert properties == published["properties"]
            points = published["geometry"]["coordinates"]
            while isinstance(points[0][0], list):
                points = [point for part in points for point in part]
            assert (west, south, east, north) == pytest.approx(
                (
                    min(p[0] for p in points),
                    min(p[1] for p in points),
                    max(p[0] for p in points),
                    max(p[1] for p in points),
                )
            )
    assert index["building"]["features"][0]["properties"]["height_m"] == 42


@pytest.mark.parametrize("query", [{"bbox": "nan,24,54,25"}, {"bbox": "54,24,54.3,24.1"}])
def test_index_rejects_invalid_queries_like_map_context(client, query):
    with override_settings(**PREVIEW):
        assert client.get("/api/v1/preview/context-index", query).status_code == 422
