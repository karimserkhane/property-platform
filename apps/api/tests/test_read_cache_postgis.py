import os
from unittest.mock import patch

import pytest
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Snapshot versions require real PostgreSQL", allow_module_level=True)

from test_onwani_postgis import feature, run  # noqa: E402

from property_platform.api import read_cache  # noqa: E402
from property_platform.modules.catalog.models import Parcel  # noqa: E402
from property_platform.modules.publication import preview  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

PREVIEW = {"DEBUG": True, "PROPERTY_PLATFORM_PARCEL_PREVIEW": True}
PARCELS = "/api/v1/preview/parcels"
BBOX = {"bbox": "54.39,24.49,54.42,24.52"}


@pytest.fixture(autouse=True)
def empty_store():
    read_cache.store.clear()
    yield
    read_cache.store.clear()


def test_unchanged_data_is_revalidated_without_a_body(client):
    run([feature(1, "RT1_C1")])
    with override_settings(**PREVIEW):
        first = client.get(PARCELS, BBOX)
        etag = first["ETag"]
        assert first.status_code == 200
        assert etag.startswith('W/"')
        assert first["Cache-Control"] == "private, no-cache"
        again = client.get(PARCELS, BBOX, HTTP_IF_NONE_MATCH=etag)
        assert again.status_code == 304
        assert again.content == b""
        assert again["ETag"] == etag
        other = client.get(PARCELS, {**BBOX, "q": "RT1"}, HTTP_IF_NONE_MATCH=etag)
        assert other.status_code == 200
        assert other["ETag"] != etag


def test_any_committed_change_invalidates_bodies_and_etags(client):
    run([feature(1, "RT1_C1")])
    with override_settings(**PREVIEW):
        before = client.get(PARCELS, BBOX)
        Parcel.objects.update(land_use="School")
        after = client.get(PARCELS, BBOX, HTTP_IF_NONE_MATCH=before["ETag"])
    assert after.status_code == 200
    assert after["ETag"] != before["ETag"]
    assert after.json()["features"][0]["properties"]["land_use"] == "School"


def test_repeated_reads_are_served_from_the_bounded_store(client):
    run([feature(1, "RT1_C1")])
    with (
        override_settings(**PREVIEW),
        patch.object(preview, "features", wraps=preview.features) as computed,
    ):
        first = client.get(PARCELS, BBOX)
        second = client.get(PARCELS, BBOX)
    assert computed.call_count == 1
    assert second.content == first.content
    assert second["ETag"] == first["ETag"]
    assert second["Content-Type"] == first["Content-Type"]
    assert read_cache.store.size == len(first.content)


def test_tiles_are_cached_with_their_media_type(client):
    run([feature(1, "RT1_C1")])
    path = "/api/v1/preview/parcel-tiles/14/10668/7041"
    with override_settings(**PREVIEW):
        first = client.get(path)
        second = client.get(path, HTTP_IF_NONE_MATCH=first["ETag"])
        third = client.get(path)
    assert first.status_code == 200
    assert first["Content-Type"] == "application/vnd.mapbox-vector-tile"
    assert second.status_code == 304
    assert third.content == first.content
    assert third["Content-Type"] == first["Content-Type"]


def test_errors_and_a_closed_preview_are_never_cached(client):
    run([feature(1, "RT1_C1")])
    with override_settings(**PREVIEW):
        cached = client.get(PARCELS, BBOX)
        rejected = client.get(PARCELS, {**BBOX, "territory": "dubai"})
    assert rejected.status_code == 409
    assert "ETag" not in rejected
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=False):
        closed = client.get(PARCELS, BBOX, HTTP_IF_NONE_MATCH=cached["ETag"])
    assert closed.status_code == 403
    assert "ETag" not in closed
