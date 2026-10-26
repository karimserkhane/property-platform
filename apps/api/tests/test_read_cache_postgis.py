import os
from unittest.mock import patch

import pytest
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Snapshot versions require real PostgreSQL", allow_module_level=True)

from test_onwani_postgis import feature, run  # noqa: E402
from test_projects_postgis import project_input  # noqa: E402, F401

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


TILE = "/api/v1/preview/parcel-tiles/14/10668/7041"


def test_a_write_to_another_table_family_keeps_the_stored_body(client):
    from property_platform.modules.catalog import queries
    from property_platform.modules.evidence.models import Source

    run([feature(1, "RT1_C1")])
    with (
        override_settings(**PREVIEW),
        patch.object(queries, "parcel_tile", wraps=queries.parcel_tile) as computed,
    ):
        first = client.get(TILE)
        entry = read_cache.store.get(TILE)
        assert entry.family.tables == (("real_estate", "parcel"),)
        snapshot = read_cache.data_version()
        Source.objects.update(name="Renamed source")  # Journaled, but never read by tiles.
        assert read_cache.data_version() != snapshot
        again = client.get(TILE, HTTP_IF_NONE_MATCH=first["ETag"])
        body = client.get(TILE)
    assert computed.call_count == 1
    assert again.status_code == 304
    assert again["ETag"] == first["ETag"]
    assert body.content == first.content


def test_a_write_to_the_family_invalidates_the_stored_body(client):
    run([feature(1, "RT1_C1")])
    with override_settings(**PREVIEW):
        first = client.get(TILE)
        Parcel.objects.update(land_use="School")
        again = client.get(TILE, HTTP_IF_NONE_MATCH=first["ETag"])
    assert again.status_code == 200
    assert again["ETag"] != first["ETag"]


def test_a_writer_in_progress_when_stored_invalidates_once_committed(client):
    """A commit with an older revision id than the latest visible one is still seen."""
    import threading

    from django.db import connection, transaction

    run([feature(1, "RT1_C1"), feature(2, "RT1_C2")])
    first_id, second_id = Parcel.objects.order_by("pk").values_list("pk", flat=True)
    written, release = threading.Event(), threading.Event()

    def slow_writer():
        try:
            with transaction.atomic():
                Parcel.objects.filter(pk=first_id).update(land_use="School")
                written.set()
                release.wait(10)
        finally:
            connection.close()

    writer = threading.Thread(target=slow_writer)
    writer.start()
    try:
        assert written.wait(10)
        Parcel.objects.filter(pk=second_id).update(land_use="Retail")  # Newer revision id.
        with override_settings(**PREVIEW):
            first = client.get(PARCELS, BBOX)
            entry = read_cache.store.get(f"{PARCELS}?bbox={BBOX['bbox'].replace(',', '%2C')}")
            assert entry is not None and entry.family is not None and entry.family.pending
            assert client.get(PARCELS, BBOX)["ETag"] == first["ETag"]
            release.set()
            writer.join(10)
            after = client.get(PARCELS, BBOX, HTTP_IF_NONE_MATCH=first["ETag"])
    finally:
        release.set()
        writer.join(10)
    assert after.status_code == 200
    assert after["ETag"] != first["ETag"]
    uses = {f["properties"]["land_use"] for f in after.json()["features"]}
    assert {"School", "Retail"} <= uses


def test_an_exclusion_invalidates_the_reads_it_applies_to(client, project_input):  # noqa: F811
    from test_projects_postgis import ingest

    from property_platform.modules.evidence.models import HistoryExclusion, ProjectSnapshot

    _, rows, _ = project_input
    ingest(rows)
    path = "/api/v1/preview/projects"
    with override_settings(**PREVIEW):
        first = client.get(path)
        assert first.json()["total"] == 1
        assert ("evidence", "history_exclusion") in read_cache.store.get(path).family.tables
        snapshot = ProjectSnapshot.objects.get()
        HistoryExclusion.objects.create(
            dataset="project:park-view",
            record_key=snapshot.capture.url,
            capture=snapshot.capture,
            actor="reviewer",
            reason="Source identity was incorrect",
        )
        after = client.get(path, HTTP_IF_NONE_MATCH=first["ETag"])
    assert after.status_code == 200
    assert after.json()["total"] == 0
    assert after["ETag"] != first["ETag"]
