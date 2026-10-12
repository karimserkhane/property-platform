import os
from datetime import timedelta

import pytest
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("National geometry checks require real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import LineString, MultiLineString, MultiPolygon, Polygon  # noqa: E402
from django.db import connection  # noqa: E402
from django.utils import timezone  # noqa: E402

from property_platform.modules.catalog.models import Parcel, Street  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    IngestionRun,
    ParcelObservation,
    Source,
)

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def sourced_parcel(lon, lat):
    """A synthetic second provider, confined to the disposable test database."""
    namespace = f"test:provider:{lon}"
    parcel = Parcel.objects.create(
        source_namespace=namespace,
        source_record_id="1",
        code="AREA_1",
        municipality="TEST",
        district="TEST",
        geometry=MultiPolygon(
            Polygon.from_bbox((lon - 0.0005, lat - 0.0005, lon + 0.0005, lat + 0.0005)), srid=4326
        ),
    )
    source = Source.objects.create(
        key=namespace, name="Test provider", url="https://example.com/parcels"
    )
    run = IngestionRun.objects.create(source=source, connector_version="test", actor="test")
    now = timezone.now()
    run.status, run.finished_at = "succeeded", now
    run.save()
    capture = Capture.objects.create(
        run=run,
        url=source.url,
        fetched_started_at=now - timedelta(seconds=1),
        fetched_at=now,
        http_status=200,
        content_sha256="a" * 64,
        payload=b"{}",
        byte_length=2,
    )
    ParcelObservation.objects.create(
        parcel=parcel,
        capture=capture,
        source_record_id="1",
        field_path="test",
        raw_attributes={},
        record_sha256="b" * 64,
        mapping_version="test",
    )
    return parcel


@pytest.mark.parametrize("lon,lat", [(52.0, 24.0), (55.3, 25.2), (56.4, 25.6)])
def test_provider_independent_reads_and_geodesic_measurements_across_uae(client, lon, lat):
    parcel = sourced_parcel(lon, lat)
    for key, offset in [("near", 0.0007), ("far", 0.0013)]:
        Street.objects.create(
            source_namespace="test:streets",
            source_record_id=key,
            name=key,
            geometry=MultiLineString(
                LineString((lon - 0.001, lat + offset), (lon + 0.001, lat + offset)), srid=4326
            ),
        )
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        listing = client.get(
            "/api/v1/preview/parcels",
            {"bbox": f"{lon - 0.01},{lat - 0.01},{lon + 0.01},{lat + 0.01}"},
        )
        response = client.get(f"/api/v1/preview/parcels/{parcel.id}")
        scoped = client.get(f"/api/v1/preview/parcels/{parcel.id}", {"territory": "al-reem-island"})
    assert listing.status_code == response.status_code == 200
    assert (
        listing.json()["features"][0]["properties"]["source_url"] == "https://example.com/parcels"
    )
    assert scoped.status_code == 404
    detail = response.json()
    assert detail["source"]["name"] == "Test provider"
    assert [street["name"] for street in detail["streets"]] == ["near"]
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT ST_Area(geometry::geography) FROM real_estate.parcel WHERE id=%s", [parcel.id]
        )
        area = cursor.fetchone()[0]
        cursor.execute(
            "SELECT ST_Distance(ST_Centroid(p.geometry)::geography, s.geometry::geography) "
            "FROM real_estate.parcel p CROSS JOIN real_estate.street s "
            "WHERE p.id=%s AND s.name='near'",
            [parcel.id],
        )
        distance = cursor.fetchone()[0]
    assert detail["area_m2"] == pytest.approx(area, abs=0.06)
    assert detail["streets"][0]["distance_m"] == pytest.approx(distance, abs=0.06)


def test_coverage_registry_counts_only_activated_sources(client):
    from test_onwani_postgis import feature, run

    run([feature()])
    sourced_parcel(55.3, 25.2)
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get("/api/v1/preview/territories")
    assert response.status_code == 200
    rows = {item["id"]: item for item in response.json()["territories"]}
    assert rows["al-reem-island"]["parcel_count"] == 1
    assert rows["al-reem-island"]["queryable"] is True
    assert rows["dubai"]["parcel_count"] == 0
    assert rows["dubai"]["queryable"] is False
