import os

import pytest
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Canonical identity queries require real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import MultiPolygon, Point, Polygon  # noqa: E402
from test_onwani_postgis import feature, run  # noqa: E402

from property_platform.modules.catalog.map_queries import map_rows  # noqa: E402
from property_platform.modules.catalog.models import AdministrativeArea, Parcel, Place  # noqa: E402
from property_platform.modules.catalog.queries import parcel_counts, parcel_identity  # noqa: E402
from property_platform.modules.evidence.maps.onwani import SOURCE_KEY  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def test_reconciled_duplicate_preserves_links_and_is_not_counted_or_drawn_twice(client):
    run([feature(1, "RT1_C1")])
    canonical = Parcel.objects.get()
    values = {
        field: getattr(canonical, field)
        for field in (
            "official_plot_id",
            "code",
            "municipality",
            "district",
            "community",
            "land_use",
            "construction_status",
        )
    }
    duplicate = Parcel.objects.create(
        source_namespace=SOURCE_KEY,
        source_record_id="new-provider-id",
        geometry=canonical.geometry,
        superseded_by=canonical,
        **values,
    )
    assert parcel_counts([SOURCE_KEY]) == {SOURCE_KEY: 1}
    assert parcel_identity(parcel_id=duplicate.id)["id"] == canonical.id
    assert parcel_identity(parcel_id=duplicate.id, namespaces=["other-provider"]) is None
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get(
            "/api/v1/preview/parcels", {"bbox": "54.39,24.49,54.42,24.52", "limit": 10}
        )
        assert response.status_code == 200
        assert [item["id"] for item in response.json()["features"]] == [str(canonical.id)]
        detail = client.get(f"/api/v1/preview/parcels/{duplicate.id}")
        assert detail.status_code == 200
        assert detail.json()["id"] == str(canonical.id)
        assert detail.json()["source"]["retrieved_at"]
    assert Parcel.objects.count() == 2


def test_map_excludes_superseded_areas_and_only_links_places_to_canonical_parcels():
    run([feature(1, "RT1_C1")])
    parcel = Parcel.objects.get()
    Parcel.objects.create(
        source_namespace=SOURCE_KEY,
        source_record_id="renumbered",
        municipality=parcel.municipality,
        district=parcel.district,
        geometry=parcel.geometry,
        superseded_by=parcel,
    )
    shape = MultiPolygon(Polygon.from_bbox((54.39, 24.49, 54.42, 24.52)), srid=4326)
    canonical = AdministrativeArea.objects.create(
        source_namespace="test:community", source_record_id="1", name="RT1", geometry=shape
    )
    AdministrativeArea.objects.create(
        source_namespace="test:community",
        source_record_id="2",
        name="RT1",
        geometry=shape,
        superseded_by=canonical,
    )
    place = Place.objects.create(
        source_namespace="test:place",
        source_record_id="1",
        name="Inside canonical parcel",
        geometry=Point(parcel.geometry.point_on_surface.coords, srid=4326),
    )
    areas, truncated = map_rows("administrative_area", (54.39, 24.49, 54.42, 24.52))
    assert truncated is False
    assert [row["id"] for row in areas] == [canonical.id]
    places, _ = map_rows("place", (54.39, 24.49, 54.42, 24.52))
    assert places[0]["id"] == place.id
    assert places[0]["parcel_ids"] == [parcel.id]
