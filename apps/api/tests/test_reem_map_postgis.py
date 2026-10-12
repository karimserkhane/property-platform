import json
import os
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from django.test import override_settings

if os.environ.get("LIWA_TEST_POSTGIS") != "1":
    pytest.skip("Map integration requires real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import LineString, MultiLineString, MultiPolygon, Polygon  # noqa: E402

from liwa.modules.catalog.models import AdministrativeArea, Building, Place, Street  # noqa: E402
from liwa.modules.evidence import map_sources as protocol  # noqa: E402
from liwa.modules.evidence.map_import import import_map_layer  # noqa: E402
from liwa.modules.evidence.models import Capture, IngestionRun, MapObservation  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def receipt():
    now = datetime.now(UTC)
    return {
        "url": protocol.OSM_URL,
        "fetched_started_at": now,
        "fetched_at": now,
        "http_status": 200,
        "etag": "",
        "last_modified_raw": "",
    }


def osm():
    return {
        "osm3s": {"timestamp_osm_base": "2026-10-11T00:00:00Z"},
        "elements": [
            {
                "type": "way",
                "id": 1,
                "timestamp": "2026-01-01T00:00:00Z",
                "version": 1,
                "tags": {
                    "building": "apartments",
                    "name": "Real source building",
                    "height": "42",
                    "building:levels": "12",
                },
                "geometry": [
                    {"lon": lon, "lat": lat}
                    for lon, lat in [(54.4, 24.5), (54.401, 24.5), (54.401, 24.501), (54.4, 24.5)]
                ],
            },
            {
                "type": "node",
                "id": 2,
                "timestamp": "2026-01-01T00:00:00Z",
                "version": 1,
                "lon": 54.405,
                "lat": 24.505,
                "tags": {"amenity": "school", "name": "Example school"},
            },
        ],
    }


def district():
    return AdministrativeArea.objects.create(
        source_namespace="test",
        source_record_id="district",
        name="AL REEM ISLAND",
        kind="district",
        geometry=MultiPolygon(Polygon.from_bbox((54.39, 24.49, 54.42, 24.52)), srid=4326),
    )


def collect(data):
    return import_map_layer(
        layer="osm", actor="test", replay=(json.dumps(data).encode(), receipt())
    )


def test_osm_centroid_repeat_reconciliation_and_geometry_audit(client):
    district()
    first = collect(osm())
    assert first.summary["created"] == 3
    building = Building.objects.get()
    assert building.height_m == 42 and building.levels == 12
    assert Place.objects.count() == 2
    collect(osm())
    assert Building.objects.get().pk == building.pk
    assert Building.objects.get().revision == 1
    original = MapObservation.objects.filter(building=building).first().record_sha256
    changed = osm()
    changed["elements"][0]["geometry"][1]["lon"] += 0.0001
    collect(changed)
    assert Building.objects.get().revision == 2
    assert MapObservation.objects.filter(building=building).latest("id").record_sha256 != original
    with override_settings(DEBUG=True, LIWA_PARCEL_PREVIEW=True):
        result = client.get("/api/v1/preview/map-context", {"bbox": "54.39,24.49,54.42,24.52"})
    assert result.status_code == 200
    assert len(result.json()["place"]["features"]) == 2
    source = result.json()["building"]["features"][0]["properties"]["source"]
    assert source["reliability"] == "community"
    assert source["published_at"].startswith("2026-01-01")


def test_truncated_replay_never_falls_back_or_replaces_existing():
    district()
    collect(osm())
    with patch("liwa.modules.evidence.map_sources.fetch_url") as fetch:
        with pytest.raises(ValueError):
            collect({**osm(), "remark": "timeout"})
        fetch.assert_not_called()
    assert Building.objects.count() == 1
    assert Building.objects.get().revision == 1
    assert IngestionRun.objects.filter(status="failed").count() == 1


def test_audit_failure_rolls_back_geometry_but_keeps_capture():
    district()
    with patch(
        "liwa.modules.evidence.map_import.MapObservation.objects.create", side_effect=RuntimeError
    ):
        with pytest.raises(RuntimeError):
            collect(osm())
    assert Building.objects.count() == Place.objects.count() == Street.objects.count() == 0
    assert Capture.objects.count() == 1
    assert IngestionRun.objects.get().status == "failed"


def test_spatial_candidates_preserve_overlap_without_assigning_project_identity(client):
    from test_onwani_postgis import feature, run

    district()
    run([feature(1, "RT1_C1"), feature(2, "RT1_C2")])
    collect(osm())
    with override_settings(DEBUG=True, LIWA_PARCEL_PREVIEW=True):
        result = client.get(
            "/api/v1/preview/map-context", {"bbox": "54.39,24.49,54.42,24.52"}
        ).json()
    building_place = next(
        f for f in result["place"]["features"] if f["properties"]["kind"] == "apartments"
    )
    assert len(building_place["properties"]["parcel_ids"]) == 2
    assert "project_id" not in building_place["properties"]


def test_parcel_areas_and_nearby_distances_are_computed_by_postgis(client):
    from test_onwani_postgis import feature, run

    from liwa.modules.catalog.models import Parcel

    run([feature()])
    Street.objects.create(
        source_namespace="test",
        source_record_id="street",
        name="Nearby road",
        geometry=MultiLineString(LineString((54.39, 24.50333), (54.42, 24.50333)), srid=4326),
    )
    with override_settings(DEBUG=True, LIWA_PARCEL_PREVIEW=True):
        result = client.get(f"/api/v1/preview/parcels/{Parcel.objects.get().pk}")
    assert result.status_code == 200
    assert result.json()["area_m2"] > 100
    assert result.json()["streets"][0]["name"] == "Nearby road"
    assert 0 <= result.json()["streets"][0]["distance_m"] < 5
