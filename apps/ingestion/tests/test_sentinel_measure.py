import json
from datetime import UTC, datetime

import httpx
import numpy as np
import pytest
from test_sentinel_activity import feature
from test_sentinel_windows import VALUES, parcel, ranges, scene

from property_platform_ingestion.collectors.sentinel_measure import (
    ActivityCollector,
    replay_signal,
)
from property_platform_ingestion.collectors.sentinel_windows import SEARCH_URL, WindowError

BEFORE, AFTER = "S2C_40RBN_20260801_0_L2A", "S2C_40RBN_20260901_0_L2A"
CLEAR = np.full((32, 32), 5, dtype=np.uint8)


def search(items):
    """Earth Search stub listing ``items`` on two pages of one item each."""

    def handler(request):
        number = int(request.url.params.get("next", 0))
        body = {
            "type": "FeatureCollection",
            "features": [items[number]],
            "numberMatched": len(items),
            "links": [{"rel": "next", "href": f"{SEARCH_URL}?limit=100&next={number + 1}"}],
        }
        return httpx.Response(200, stream=httpx.ByteStream(json.dumps(body).encode()))

    return httpx.MockTransport(handler)


def collector():
    before, before_files = scene(BEFORE, VALUES, CLEAR)
    changed = {key: value + 1000 for key, value in VALUES.items()}
    after, after_files = scene(AFTER, changed, CLEAR)
    items = [
        feature(BEFORE, "2026-08-01T07:00:00Z", 2.0),
        feature(AFTER, "2026-09-01T07:00:00Z", 3.0),
    ]
    return ActivityCollector(
        end=datetime(2026, 10, 25, tzinfo=UTC),
        search_transport=search(items),
        range_transport=ranges(before_files | after_files),
    )


def test_scenes_keep_every_page_and_cite_the_page_of_each_scene():
    with collector() as session:
        found = session.scenes((54.38, 24.47, 54.43, 24.52))
    assert [page["receipt"]["http_status"] for page in found["pages"]] == [200, 200]
    assert [(row["scene_id"], row["page"]) for row in found["scenes"]] == [(BEFORE, 0), (AFTER, 1)]


def test_windows_are_captured_and_the_signal_replays_from_capture_bytes():
    geometry = parcel(8, 8, 20, 16)
    with collector() as session:
        scenes = session.scenes((54.38, 24.47, 54.43, 24.52))["scenes"]
        windows = [session.window(row, geometry) for row in scenes]
        assert session.window(scenes[0], parcel(60, 4, 70, 10)) is None
    receipt = windows[0]["receipt"]
    assert (receipt["http_status"], receipt["acquisition_method"]) == (
        206,
        "sentinel_cog_window_ranges",
    )
    assert receipt["url"].endswith("/items/" + BEFORE)
    result = ActivityCollector.signal(windows[0]["payload"], windows[1]["payload"], geometry)
    assert (result["status"], result["changed_pixels"], result["level"]) == ("measured", 96, "high")
    assert result["method_version"] == ActivityCollector.method_version
    with pytest.raises(WindowError, match="grid"):
        replay_signal(
            windows[0]["payload"],
            session_window(parcel(8, 8, 21, 16), AFTER),
            geometry,
        )


def session_window(geometry, identity):
    with collector() as session:
        row = next(
            item
            for item in session.scenes((54.38, 24.47, 54.43, 24.52))["scenes"]
            if item["scene_id"] == identity
        )
        return session.window(row, geometry)["payload"]
