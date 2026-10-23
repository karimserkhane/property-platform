import math
import os

import pytest
from django.contrib.gis.geos import Point
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Parcel tiles require real PostGIS", allow_module_level=True)

from test_onwani_postgis import feature, run  # noqa: E402

from property_platform.modules.catalog.models import Parcel, Place  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

PREVIEW = {"DEBUG": True, "PROPERTY_PLATFORM_PARCEL_PREVIEW": True}
BBOX = {"bbox": "54.39,24.49,54.42,24.52"}


def tile_path(lon, lat, z):
    n = 2**z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return f"/api/v1/preview/parcel-tiles/{z}/{x}/{y}"


def residential(oid, code, offset=0.0):
    row = feature(oid, code)
    row["attributes"]["ELMS_LANDUSENAME_E"] = "Residential"
    row["geometry"]["rings"] = [
        [[x + offset, y] for x, y in ring] for ring in row["geometry"]["rings"]
    ]
    return row


def marker(lon, lat, *, record, active=True, kind="research_project_marker"):
    return Place.objects.create(
        source_namespace="test:places",
        source_record_id=record,
        name=f"Project {record}",
        kind=kind,
        active=active,
        geometry=Point(lon, lat, srid=4326),
    )


def test_tiles_draw_current_footprints_by_identity_only(client):
    run([residential(1, "RT1_C1"), residential(2, "RT1_C2", offset=0.02)])
    kept, replaced = Parcel.objects.order_by("code")
    Parcel.objects.filter(pk=replaced.pk).update(superseded_by=kept)
    with override_settings(**PREVIEW):
        response = client.get(tile_path(54.403, 24.503, 14))
        assert response.status_code == 200
        assert response["Content-Type"] == "application/vnd.mapbox-vector-tile"
        assert response["Cache-Control"] == "private, no-cache"
        payload = response.content
        assert b"parcels" in payload and str(kept.pk).encode() in payload
        # Attributes stay in the published rows; the tile carries no source fields.
        assert b"RT1_C1" not in payload and b"Residential" not in payload
        replaced_tile = client.get(tile_path(54.423, 24.503, 14))
        assert str(replaced.pk).encode() not in replaced_tile.content
        assert client.get(tile_path(54.1, 24.1, 14)).status_code == 204


@pytest.mark.parametrize(
    "path", ["7/80/54", "17/86000/56000", "14/-1/7041", "14/16384/7041", "14/10668/16384"]
)
def test_tiles_reject_unserved_zooms_and_coordinates(client, path):
    with override_settings(**PREVIEW):
        response = client.get(f"/api/v1/preview/parcel-tiles/{path}")
    assert response.status_code in {404, 422}


def test_tiles_respect_territory_scope(client):
    run([residential(1, "RT1_C1")])
    with override_settings(**PREVIEW):
        path = tile_path(54.403, 24.503, 14)
        assert client.get(path, {"territory": "dubai"}).status_code == 409
        scoped = client.get(path, {"territory": "al-reem-island"})
        assert scoped.status_code == 200
        assert scoped.content == client.get(path).content


def test_index_matches_published_rows_without_footprints(client):
    run([residential(1, "RT1_C1"), residential(2, "RT1_C2", offset=0.02)])
    with override_settings(**PREVIEW):
        full = client.get("/api/v1/preview/parcels", BBOX).json()
        index = client.get("/api/v1/preview/parcel-index", BBOX).json()
    assert [item["id"] for item in index["features"]] == [item["id"] for item in full["features"]]
    for row, published in zip(index["features"], full["features"], strict=True):
        assert "geometry" not in row
        properties = row["properties"]
        for key, value in published["properties"].items():
            assert properties[key] == value
        west, south, east, north = properties["bounds"]
        lon, lat = properties["label_point"]
        assert west <= lon <= east and south <= lat <= north
        assert (west, south, east, north) == pytest.approx(
            (54.4 + (0.02 if properties["code"] == "RT1_C2" else 0), 24.5, east, 24.51)
        )
        assert properties["area_m2"] > 500_000
    assert index["classification_version"] == full["classification_version"]


def test_index_reports_active_project_markers_within_fifty_metres(client):
    run([residential(1, "RT1_C1")])
    inside = marker(54.401, 24.501, record="inside")
    near = marker(54.4103, 24.5, record="near")  # about 30 m east of the right angle
    marker(54.4106, 24.5, record="far")  # about 60 m away
    marker(54.4102, 24.5, record="inactive", active=False)
    marker(54.4101, 24.5, record="school", kind="school")
    with override_settings(**PREVIEW):
        [row] = client.get("/api/v1/preview/parcel-index", BBOX).json()["features"]
    nearby = row["properties"]["nearby_projects"]
    assert [item["place_id"] for item in nearby] == [str(inside.pk), str(near.pk)]
    assert nearby[0]["distance_m"] == 0
    assert 25 < nearby[1]["distance_m"] < 35


@pytest.mark.parametrize("query", [{"bbox": "nan,24,54,25"}, {**BBOX, "limit": "3001"}])
def test_index_rejects_invalid_queries_like_parcels(client, query):
    with override_settings(**PREVIEW):
        assert client.get("/api/v1/preview/parcel-index", query).status_code == 422
