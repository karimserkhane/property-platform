"""Real PostGIS, immutable graph chunks, and exact district joins."""

import hashlib
import json
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.test import override_settings
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Map analysis requires PostgreSQL/PostGIS", allow_module_level=True)

from test_adrec_postgis import execute, sales_acquisition  # noqa: E402
from test_adrec_protocol import sale  # noqa: E402

from property_platform.modules.evidence.maps.accessibility import (  # noqa: E402
    StoredGraphReceipt,
    archive_graph,
    archive_walking,
    walking_area,
)
from property_platform.modules.evidence.models import (  # noqa: E402
    AdrecMarketSnapshot,
    Capture,
    RoutingGraph,
    RowRevision,
    WalkingArea,
    WalkingRequest,
)
from property_platform.modules.publication.market_map import district_market  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def graph_receipt(payload=b"reviewed-osm-pbf"):
    now = timezone.now()
    return SimpleNamespace(
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_length=len(payload),
        http_status=200,
        chunks=lambda: iter([payload[:5], payload[5:]]),
        capture_receipt=lambda: {
            "url": "https://download.geofabrik.de/asia/gcc-states-261019.osm.pbf",
            "fetched_at": now,
            "fetched_started_at": now,
            "http_status": 200,
            "timestamp_basis": "collector_clock",
        },
    )


def store_graph(payload=b"reviewed-osm-pbf"):
    receipt = graph_receipt(payload)
    build = Mock()
    result = archive_graph(
        actor="test-routing", acquire=lambda: receipt, build=build, run_key="test-1"
    )
    assert result["status"] == "succeeded"
    return RoutingGraph.objects.get(sha256=receipt.sha256), build


def test_graph_chunks_replay_offline_preserve_acquisition_time_and_audit():
    graph, build = store_graph()
    assert b"".join(build.call_args.kwargs["parts"]) == b"reviewed-osm-pbf"
    assert graph.parts.count() == 2
    first_time = graph.capture.fetched_at
    network = Mock(side_effect=AssertionError("must remain offline"))
    rebuilt = Mock()
    result = archive_graph(
        actor="offline-rebuild", acquire=network, build=rebuilt, run_key="test-2", from_history=True
    )
    assert result["status"] == "succeeded" and network.call_count == 0
    assert b"".join(rebuilt.call_args.kwargs["parts"]) == b"reviewed-osm-pbf"
    assert graph.capture.fetched_at == first_time and Capture.objects.count() == 3
    assert (
        RowRevision.objects.filter(table_name="routing_graph_part", actor="test-routing").count()
        == 2
    )


def test_archive_mode_never_downloads_when_no_history_and_build_failure_keeps_old_ready():
    network = Mock(side_effect=AssertionError("offline"))
    result = archive_graph(
        actor="offline", acquire=network, build=Mock(), run_key="test", from_history=True
    )
    assert result["status"] == "failed" and network.call_count == 0
    graph, _ = store_graph()
    result = archive_graph(
        actor="broken",
        acquire=lambda: graph_receipt(b"new-source"),
        build=Mock(side_effect=ValueError("bad graph")),
        run_key="test",
    )
    assert result["status"] == "failed"
    graph.refresh_from_db()
    assert graph.ready and RoutingGraph.objects.filter(ready=True).count() == 1


def test_reconstruction_rejects_wrong_offsets():
    graph, _ = store_graph()
    graph.parts.filter(sequence=1).update(offset_bytes=99)
    with pytest.raises(ValueError, match="SequenceMismatch"):
        list(StoredGraphReceipt(graph).chunks())


def contour():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[54.4, 24.5], [54.405, 24.5], [54.404, 24.505], [54.4, 24.5]]],
                },
            }
        ],
    }


def test_walking_queue_computes_archived_postgis_geometry_then_retains_previous_version():
    graph, _ = store_graph()
    assert walking_area(54.4, 24.5, 10) is None
    assert WalkingRequest.objects.count() == 1
    computed = archive_walking(actor="test-walking", compute=lambda *_: contour(), run_key="test")
    assert computed["summary"]["saved"] == 1
    result = walking_area(54.4, 24.5, 10)
    assert result["graph_id"] == graph.sha256 and not result["historical"]
    assert WalkingArea.objects.get().geometry.srid == 4326
    assert json.loads(bytes(WalkingArea.objects.get().capture.payload)) == contour()
    store_graph(b"newer-source")
    assert walking_area(54.4, 24.5, 10)["historical"]
    WalkingRequest.objects.update(last_attempt_at=None)
    assert (
        archive_walking(actor="failed", compute=Mock(side_effect=ValueError()), run_key="test")[
            "summary"
        ]["failed"]
        == 1
    )
    assert walking_area(54.4, 24.5, 10)["ingested_at"] == result["ingested_at"]


@override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True)
def test_map_analysis_http_guards_and_pending_status(client):
    route = "/api/v1/preview/accessibility"
    assert client.get(route, {"longitude": 54.4, "latitude": 24.5}).status_code == 202
    for changes in [
        {"minutes": 60},
        {"longitude": "NaN"},
        {"latitude": 91},
        {"territory": "dubai"},
    ]:
        assert (
            client.get(route, {"longitude": 54.4, "latitude": 24.5, **changes}).status_code == 422
        )
    with override_settings(DEBUG=False, PROPERTY_PLATFORM_PARCEL_PREVIEW=False):
        assert client.get(route, {"longitude": 54.4, "latitude": 24.5}).status_code == 403


def test_market_uses_all_snapshot_rows_and_exact_unique_district_join():
    rows = [sale() for _ in range(6)]
    execute(sales_acquisition(rows))
    old = AdrecMarketSnapshot.objects.get()
    boundary = {
        "type": "Feature",
        "id": "district-1",
        "geometry": contour()["features"][0]["geometry"],
        "properties": {"name": rows[0]["district"], "name_ar": "", "ingested_at": timezone.now()},
    }
    districts = {
        "features": [boundary],
        "snapshot_id": None,
        "source_url": "https://example.com/districts",
    }
    with patch(
        "property_platform.modules.publication.market_map.district_map", return_value=districts
    ):
        result = district_market("al-reem-island")
        assert (
            result["mapped_sales"] == 6 and result["features"][0]["properties"]["rate_samples"] == 6
        )
        assert result["features"][0]["properties"]["median_rate"] is not None
        execute(sales_acquisition([sale()]), "later")
        assert district_market("al-reem-island")["features"][0]["properties"]["median_rate"] is None
        archived = district_market("al-reem-island", snapshot_id=old.pk)
        assert archived["mapped_sales"] == 6 and archived["historical"]
        districts["features"].append({**boundary, "id": "ambiguous-district"})
        assert district_market("al-reem-island")["unmatched_sales"] == 1
