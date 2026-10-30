import io
import json
from datetime import UTC, datetime

import httpx
import numpy as np
import pytest
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from rasterio.warp import transform_geom

from property_platform_ingestion.collectors.http import AcquisitionError, SourceHTTP
from property_platform_ingestion.collectors.sentinel_activity import change_signal
from property_platform_ingestion.collectors.sentinel_windows import (
    RANGE_BLOCK,
    SEARCH_URL,
    RangeSession,
    WindowError,
    consecutive_pairs,
    decode_window,
    encode_window,
    parcel_mask,
    read_window,
    search_page,
    search_scenes,
    search_url,
)

ROOT = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/40/R/BN/"
FILES = {"blue": "B02", "green": "B03", "red": "B04", "nir": "B08", "scl": "SCL"}
WEST, NORTH = 230000.0, 2715000.0  # UTM 40N, near Abu Dhabi island


def tiff(array, resolution):
    with MemoryFile() as memory:
        with memory.open(
            driver="GTiff",
            width=array.shape[1],
            height=array.shape[0],
            count=1,
            dtype=array.dtype,
            crs="EPSG:32640",
            transform=from_origin(WEST, NORTH, resolution, resolution),
            tiled=True,
            blockxsize=16,
            blockysize=16,
            compress="deflate",
        ) as dataset:
            dataset.write(array, 1)
        return memory.read()


def scene(identity, values, scl):
    """Synthetic 64 x 64 tile: 10 m bands from ``values`` and a 32 x 32 SCL at 20 m."""
    files = {
        key: tiff(np.full((64, 64), values[key], dtype=np.uint16), 10)
        for key in ("blue", "green", "red", "nir")
    }
    files["scl"] = tiff(scl.astype(np.uint8), 20)
    record = {
        "scene_id": identity,
        "acquired_at": datetime(2026, 9, 1, 7, tzinfo=UTC),
        "tile": "MGRS-40RBN",
        "cloud_cover": 1.0,
        "assets": {
            key: {
                "href": f"{ROOT}{identity}/{name}.tif",
                "scale": 1.0 if key == "scl" else 0.0001,
                "offset": 0.0 if key == "scl" else -0.1,
            }
            for key, name in FILES.items()
        },
    }
    return record, {record["assets"][key]["href"]: files[key] for key in FILES}


def parcel(x0, y0, x1, y1):
    """WGS84 GeoJSON of a UTM rectangle given in pixels from the tile origin."""
    ring = [(WEST + x * 10, NORTH - y * 10) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    return transform_geom(
        "EPSG:32640", "EPSG:4326", {"type": "Polygon", "coordinates": [[*ring, ring[0]]]}
    )


def local(files):
    return lambda href: io.BytesIO(files[href])


VALUES = {"blue": 1500, "green": 1600, "red": 1700, "nir": 2500}
SCL = np.full((32, 32), 5, dtype=np.uint8)
SCL[5, 5] = 9  # one 20 m cloud pixel: 2 x 2 pixels of the 10 m grid


def test_read_window_keeps_digital_numbers_and_aligns_scl():
    record, files = scene("S2C_40RBN_20260901_0_L2A", VALUES, SCL)
    window = read_window(record, parcel(8.2, 8.2, 20.6, 16.4), open_asset=local(files))
    assert (window["width"], window["height"]) == (13, 9)
    assert window["transform"][2] == pytest.approx(WEST + 80, abs=1e-6)
    assert window["transform"][5] == pytest.approx(NORTH - 80, abs=1e-6)
    assert window["arrays"]["red"].dtype == np.uint16
    assert (window["arrays"]["red"] == 1700).all()
    # The 20 m cloud pixel (rows and columns 10-11 at 10 m) lands at offset 2 in the window.
    cloud = window["arrays"]["scl"] == 9
    assert cloud.sum() == 4 and cloud[2:4, 2:4].all()
    assert window["item_url"].endswith("/items/S2C_40RBN_20260901_0_L2A")


def test_window_capture_is_deterministic_and_replays_reflectance():
    record, files = scene("S2C_40RBN_20260901_0_L2A", VALUES, SCL)
    geometry = parcel(8, 8, 20, 16)
    window = read_window(record, geometry, open_asset=local(files))
    payload = encode_window(window)
    assert payload == encode_window(read_window(record, geometry, open_asset=local(files)))
    assert "fetched_at" not in json.loads(payload)
    replay = decode_window(payload)
    assert replay["shape"] == (8, 12)
    assert replay["values"]["red"] == pytest.approx(np.full((8, 12), 0.07))
    assert parcel_mask(geometry, replay).sum() == 8 * 12


def test_replayed_windows_feed_the_change_signal():
    before, before_files = scene("S2C_40RBN_20260801_0_L2A", VALUES, np.full((32, 32), 5))
    changed = {key: value + 1000 for key, value in VALUES.items()}
    after, after_files = scene("S2C_40RBN_20260901_0_L2A", changed, np.full((32, 32), 5))
    geometry = parcel(8, 8, 20, 16)
    windows = [
        decode_window(encode_window(read_window(item, geometry, open_asset=local(files))))
        for item, files in ((before, before_files), (after, after_files))
    ]
    result = change_signal(
        windows[0]["values"], windows[1]["values"], parcel_mask(geometry, windows[0])
    )
    assert result["status"] == "measured"
    assert (result["clear_pixels"], result["changed_pixels"], result["level"]) == (96, 96, "high")


@pytest.mark.parametrize("box", [(-2, 4, 10, 10), (60, 4, 70, 10), (4, 60, 10, 70)])
def test_read_window_refuses_parcels_outside_the_tile(box):
    record, files = scene("S2C_40RBN_20260901_0_L2A", VALUES, SCL)
    with pytest.raises(WindowError, match="inside"):
        read_window(record, parcel(*box), open_asset=local(files))


def test_read_window_refuses_oversized_parcels(monkeypatch):
    from property_platform_ingestion.collectors import sentinel_windows

    monkeypatch.setattr(sentinel_windows, "MAX_WINDOW_PIXELS", 10)
    record, files = scene("S2C_40RBN_20260901_0_L2A", VALUES, SCL)
    with pytest.raises(WindowError, match="size"):
        read_window(record, parcel(2, 2, 20, 6), open_asset=local(files))


@pytest.mark.parametrize(
    "change",
    [
        lambda doc: doc.update(format="other"),
        lambda doc: doc["arrays"]["red"].update(data=doc["arrays"]["red"]["data"][:-8]),
        lambda doc: doc["arrays"]["scl"].update(dtype="uint16"),
        lambda doc: doc.update(width=1000),
        lambda doc: doc.pop("transform"),
    ],
)
def test_decode_window_refuses_altered_captures(change):
    record, files = scene("S2C_40RBN_20260901_0_L2A", VALUES, SCL)
    document = json.loads(
        encode_window(read_window(record, parcel(8, 8, 12, 12), open_asset=local(files)))
    )
    change(document)
    with pytest.raises(WindowError):
        decode_window(json.dumps(document).encode())


def ranges(files, *, status=206, log=None):
    def handler(request):
        payload = files[str(request.url)]
        if request.method == "HEAD":
            if log is not None:
                log.append(("HEAD", 0, 0))
            return httpx.Response(200, headers={"Content-Length": str(len(payload))})
        start, end = (int(value) for value in request.headers["Range"][6:].split("-"))
        if log is not None:
            log.append(("GET", start, end - start + 1))
        return httpx.Response(status, content=payload[start : end + 1])

    return httpx.MockTransport(handler)


def test_range_session_reads_windows_with_bounded_ranges():
    record, files = scene("S2C_40RBN_20260901_0_L2A", VALUES, SCL)
    log = []
    with RangeSession(transport=ranges(files, log=log)) as session:
        window = read_window(record, parcel(8, 8, 20, 16), open_asset=session.open)
        fetched = [size for method, _, size in log if method == "GET"]
        assert session.transferred == sum(fetched) == window["transferred_bytes"] > 0
    assert (window["arrays"]["nir"] == 2500).all()
    # GDAL's many small reads hit the block cache: one length and one block per asset.
    assert [method for method, _, _ in log].count("HEAD") == len(fetched) == 5
    assert all(start % RANGE_BLOCK == 0 for _, start, _ in log)


def test_range_session_requires_partial_responses_and_reviewed_hosts():
    record, files = scene("S2C_40RBN_20260901_0_L2A", VALUES, SCL)
    with RangeSession(transport=ranges(files, status=200)) as session:
        with pytest.raises(AcquisitionError, match="byte ranges"):
            read_window(record, parcel(8, 8, 20, 16), open_asset=session.open)
        with pytest.raises(AcquisitionError, match="host"):
            session.open("https://example.com/sentinel-s2-l2a-cogs/B04.tif")
    with RangeSession(transport=ranges(files), max_session_bytes=64) as session:
        with pytest.raises(AcquisitionError, match="budget"):
            read_window(record, parcel(8, 8, 20, 16), open_asset=session.open)


@pytest.mark.parametrize("enforced", [False, True])
def test_range_session_follows_the_collection_switch(
    enforced, enforce_collection, forbid_collection
):
    enforce_collection(enforced)
    forbid_collection("sentinel-cogs.s3.us-west-2.amazonaws.com")
    record, files = scene("S2C_40RBN_20260901_0_L2A", VALUES, SCL)
    log = []
    with RangeSession(transport=ranges(files, log=log)) as session:
        if enforced:
            with pytest.raises(AcquisitionError, match="forbid"):
                read_window(record, parcel(8, 8, 20, 16), open_asset=session.open)
        else:
            window = read_window(record, parcel(8, 8, 20, 16), open_asset=session.open)
            assert (window["arrays"]["nir"] == 2500).all()
    assert (log == []) is enforced


END = datetime(2026, 10, 25, tzinfo=UTC)
BBOX = (54.38, 24.47, 54.43, 24.52)


def search_pages(pages):
    """Earth Search stub: page ``n`` of ``pages`` links page ``n + 1``, as the API does."""
    requested = []

    def handler(request):
        number = int(request.url.params.get("next", 0))
        requested.append(str(request.url))
        items, matched = pages[number]
        body = {
            "type": "FeatureCollection",
            "features": [{"id": item} for item in items],
            "numberMatched": matched,
            "links": [{"rel": "next", "href": f"{SEARCH_URL}?limit=100&next={number + 1}"}],
        }
        return httpx.Response(200, stream=httpx.ByteStream(json.dumps(body).encode()))

    return httpx.MockTransport(handler), requested


def collect(pages):
    transport, requested = search_pages(pages)
    with SourceHTTP([SEARCH_URL], transport=transport, min_interval_seconds=0) as http:
        return search_scenes(http, BBOX, end=END), requested, http.acquisitions


def test_search_url_covers_the_months_before_the_end():
    url = search_url(BBOX, end=END)
    assert url.startswith("https://earth-search.aws.element84.com/v1/search?collections=")
    assert "datetime=2026-04-22T00%3A00%3A00Z%2F2026-10-25T00%3A00%3A00Z" in url
    with pytest.raises(ValueError):
        search_url((54.4, 24.5, 54.3, 24.6), end=END)


def test_search_scenes_follows_pages_until_the_matched_total():
    features, requested, acquisitions = collect({0: (["a", "b"], 3), 1: (["c"], 3)})
    assert [feature["id"] for feature in features] == ["a", "b", "c"]
    assert len(requested) == len(acquisitions) == 2
    # The next link of the last page is not followed once the total is reached.
    features, requested, _ = collect({0: (["a"], 1)})
    assert len(features) == len(requested) == 1


@pytest.mark.parametrize(
    "pages",
    [
        {0: (["a"], 2), 1: ([], 2)},
        {0: (["a"], 2), 1: (["a"], 2)},
        {number: ([str(number)], 99) for number in range(6)},
    ],
    ids=["ends-early", "repeats", "too-many-pages"],
)
def test_search_scenes_refuses_incomplete_results(pages):
    with pytest.raises(AcquisitionError):
        collect(pages)


def test_search_page_rejects_foreign_links_and_bodies():
    with pytest.raises(AcquisitionError):
        search_page(b"<html>")
    with pytest.raises(AcquisitionError, match="link"):
        search_page(
            b'{"type":"FeatureCollection","features":[],"numberMatched":0,'
            b'"links":[{"rel":"next","href":"https://example.com/search?next=1"}]}'
        )


def test_consecutive_pairs_stay_on_one_tile():
    def item(tile, month):
        return {"tile": tile, "acquired_at": datetime(2026, month, 1, tzinfo=UTC)}

    scenes = [item("MGRS-40RBN", 7), item("MGRS-40RBN", 8), item("MGRS-40RBN", 9)]
    scenes += [item("MGRS-40RCN", 8), item("MGRS-40RCN", 9)]
    pairs = consecutive_pairs(scenes)
    assert [(a["tile"], a["acquired_at"].month, b["acquired_at"].month) for a, b in pairs] == [
        ("MGRS-40RBN", 7, 8),
        ("MGRS-40RBN", 8, 9),
        ("MGRS-40RCN", 8, 9),
    ]
