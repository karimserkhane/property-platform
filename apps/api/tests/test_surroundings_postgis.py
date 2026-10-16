"""Real distance, source and overlap semantics on PostGIS, never a live remote service."""

import os
from uuid import uuid4

import pytest
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Neighbourhood reads require real PostGIS", allow_module_level=True)

from test_onwani_postgis import feature, run  # noqa: E402
from test_reem_map_postgis import collect, district  # noqa: E402

from property_platform.modules.catalog.models import Parcel, Place  # noqa: E402
from property_platform.modules.publication.surroundings import surroundings  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def amenities():
    return {
        "osm3s": {"timestamp_osm_base": "2026-10-11T00:00:00Z"},
        "elements": [
            {
                "type": "node",
                "id": i,
                "version": 1,
                "timestamp": "2026-10-01T00:00:00Z",
                "lon": 54.405 + i * 0.0001,
                "lat": 24.505,
                "tags": {**tags, "name": name},
            }
            for i, (name, tags) in enumerate(
                [
                    ("School", {"amenity": "school"}),
                    ("Grocer", {"shop": "supermarket"}),
                    ("Clinic", {"amenity": "clinic"}),
                    ("Park", {"leisure": "park"}),
                    ("Cafe", {"amenity": "cafe"}),
                    ("Mosque", {"amenity": "place_of_worship", "religion": "muslim"}),
                    ("Station", {"railway": "station"}),
                    ("Housing, not an amenity", {"building": "apartments"}),
                    ("", {"highway": "bus_stop"}),
                ],
                1,
            )
        ],
    }


def test_overlaps_keep_both_uses_but_exclude_parent_perimeters_and_superseded_records(client):
    school, data, sector = feature(1, "RT4_P22"), feature(2, "RT4_TMP4"), feature(3, "RT4")
    school["attributes"].update(ELMS_LANDUSENAME_E="Schools", OWNERSHIPTYPE="PERMANENT")
    data["attributes"].update(ELMS_LANDUSENAME_E="Data Center", OWNERSHIPTYPE="TEMPORARY")
    sector["geometry"]["rings"] = [[[54.39, 24.49], [54.42, 24.49], [54.42, 24.52], [54.39, 24.49]]]
    run([school, data, sector])
    parcel = Parcel.objects.get(code="RT4_TMP4")
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        result = client.get(f"/api/v1/preview/parcels/{parcel.id}")
    assert result.status_code == 200
    body = result.json()
    assert body["land_use"] == "Data Center"
    assert len(body["overlapping_parcels"]) == 1
    other = body["overlapping_parcels"][0]
    assert other["code"] == "RT4_P22" and other["use_types"] == ["school"]
    assert other["ownership"] == "PERMANENT"
    assert other["source"]["retrieved_at"] and other["source"]["ingested_at"]
    assert other["source"]["url"].startswith("https://onwani.abudhabi.ae/")
    assert body["attributes"]["ownership"] == "TEMPORARY"


def test_neighbourhood_classifies_captured_tags_and_keeps_real_distances_and_provenance(client):
    district()
    collect(amenities())
    anchor = Place.objects.get(name="Cafe")
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get(
            f"/api/v1/preview/surroundings/place/{anchor.id}", {"territory": "al-reem-island"}
        )
    assert response.status_code == 200
    body = response.json()
    assert body["distance_basis"] == "point" and body["radius_m"] == 1500
    groups = {row["key"]: row["items"] for row in body["groups"]}
    assert set(groups) == {"education", "shopping", "health", "leisure", "worship", "transport"}
    assert groups["shopping"][0]["name"] == "Grocer"
    assert any("bus_stop" in item["use_types"] for item in groups["transport"])
    school = groups["education"][0]
    assert school["use_types"] == ["school"] and 35 < school["distance_m"] < 45
    assert school["source"]["reliability"] == "community"
    assert school["source"]["published_at"].startswith("2026-10-01")
    assert school["source"]["retrieved_at"] and "_capture_id" not in school["source"]


def test_nearby_is_bounded_and_never_uses_an_unrecorded_location_or_crosses_collection_scope():
    district()
    data = amenities()
    prototype = data["elements"][0]
    for i in range(20, 30):
        data["elements"].append({**prototype, "id": i, "lon": 54.405 + i * 0.0001})
    data["elements"].append({**prototype, "id": 99, "lon": 54.425})
    collect(data)
    anchor = Place.objects.get(name="Cafe")
    result = surroundings("place", anchor.id)
    schools = next(row["items"] for row in result["groups"] if row["key"] == "education")
    assert len(schools) == 3
    assert schools == sorted(schools, key=lambda row: row["distance_m"])
    assert all(row["distance_m"] <= 1500 for group in result["groups"] for row in group["items"])
    assert surroundings("place", uuid4()) is None
    assert surroundings("place", anchor.id, namespaces=("another:scope",)) is None


def test_empty_neighbourhood_is_explicit_not_a_claim_that_no_facilities_exist():
    run([feature()])
    result = surroundings("parcel", Parcel.objects.get().id)
    assert result == {
        "radius_m": 1500,
        "distance_basis": "centroid",
        "truncated": False,
        "groups": [],
    }
