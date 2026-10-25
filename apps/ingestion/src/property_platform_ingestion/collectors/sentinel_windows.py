"""Sentinel-2 acquisition for the activity signal: STAC search and bounded COG windows.

Only HTTPS byte ranges of the reviewed Sentinel-2 COG host are read, never whole tiles.
A parcel window is encoded as a deterministic JSON capture of the original digital
numbers, so a measurement can be replayed from captures alone. The change index itself
is in ``sentinel_activity``. See docs/engineering/CONSTRUCTION_ACTIVITY.md.
"""

import base64
import io
import json
import math
import ssl
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlsplit

import httpx
import numpy as np

from .http import AcquisitionError, checked_url
from .sentinel_activity import ASSET_HOST, BANDS, CLASSIFICATION, COLLECTION, reflectance

SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
ITEM_URL = f"https://earth-search.aws.element84.com/v1/collections/{COLLECTION}/items/"
WINDOW_FORMAT = "sentinel-activity-window-v1"
SEARCH_LIMIT = 100
# One page of 100 items is about 2 MB; six months over two MGRS tiles is two pages.
SEARCH_MAX_BYTES = 8 * 1024 * 1024
MAX_SEARCH_PAGES = 5
# A window of at most 256 x 256 pixels at 10 m (2.56 km a side); larger parcels are
# master plans whose change share would not describe one building site.
MAX_WINDOW_PIXELS = 256
PIXEL_TOLERANCE = 1e-6
RANGE_BLOCK = 64 * 1024
MAX_RANGE_BYTES = 8 * 1024 * 1024
MAX_ASSET_BYTES = 32 * 1024 * 1024
MAX_SESSION_BYTES = 512 * 1024 * 1024
_DTYPES = {"uint16": np.dtype("<u2"), "uint8": np.dtype("u1")}


class WindowError(ValueError):
    """A parcel window cannot be read or replayed as a reviewed Sentinel-2 window."""


def search_url(bbox, *, end, months=6):
    """Earth Search query of L2A items over a WGS84 bbox for the months before ``end``."""
    west, south, east, north = (float(value) for value in bbox)
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Invalid search bbox")
    if end.tzinfo is None or not 1 <= months <= 24:
        raise ValueError("Invalid search period")
    start = end - timedelta(days=31 * months)
    query = {
        "collections": COLLECTION,
        "bbox": ",".join(f"{value:.6f}" for value in (west, south, east, north)),
        "datetime": f"{_stamp(start)}/{_stamp(end)}",
        "limit": SEARCH_LIMIT,
    }
    return f"{SEARCH_URL}?{urlencode(query)}"


def _stamp(value):
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def search_page(payload):
    """Items, total matched and next page URL of one Earth Search response page."""
    try:
        collection = json.loads(payload)
        features = collection["features"]
        matched = collection["numberMatched"]
    except (TypeError, ValueError, KeyError) as exc:
        raise AcquisitionError("Malformed Sentinel-2 search response") from exc
    if (
        collection.get("type") != "FeatureCollection"
        or not isinstance(features, list)
        or type(matched) is not int
        or matched < 0
    ):
        raise AcquisitionError("Malformed Sentinel-2 search response")
    following = next(
        (
            link.get("href")
            for link in collection.get("links") or []
            if isinstance(link, dict) and link.get("rel") == "next"
        ),
        None,
    )
    if following is not None and (
        not isinstance(following, str) or not following.startswith(SEARCH_URL + "?")
    ):
        raise AcquisitionError("Unexpected Sentinel-2 search page link")
    return features, matched, following


def search_scenes(http, bbox, *, end, months=6):
    """Every item matched by one search, page by page through the reviewed endpoint.

    ``http`` is a SourceHTTP registered for SEARCH_URL, so each page is an acquisition
    with its own receipt. Earth Search links a next page even after the last item: the
    reported total decides completeness, and a search beyond MAX_SEARCH_PAGES fails
    instead of being trimmed.
    """
    url, features, seen = search_url(bbox, end=end, months=months), [], set()
    for _ in range(MAX_SEARCH_PAGES):
        acquisition = http.fetch(url, max_bytes=SEARCH_MAX_BYTES, allowed_base=SEARCH_URL)
        if acquisition.http_status != 200:
            raise AcquisitionError("Sentinel-2 search failed")
        page, matched, url = search_page(acquisition.payload)
        for feature in page:
            identity = feature.get("id") if isinstance(feature, dict) else None
            if identity in seen:
                raise AcquisitionError("Sentinel-2 search repeated an item")
            seen.add(identity)
        features.extend(page)
        if len(features) >= matched:
            if len(features) > matched:
                raise AcquisitionError("Sentinel-2 search returned unmatched items")
            return features
        if not page or url is None:
            raise AcquisitionError("Sentinel-2 search ended before its matched total")
    raise AcquisitionError("Sentinel-2 search is too large; narrow the period")


def consecutive_pairs(scenes):
    """Pairs of successive selected scenes on the same MGRS tile, oldest first."""
    pairs = []
    for before, after in zip(scenes, scenes[1:], strict=False):
        if before["tile"] == after["tile"] and before["acquired_at"] < after["acquired_at"]:
            pairs.append((before, after))
    return pairs


def _asset_url(href):
    checked_url(href)
    if not href.startswith(ASSET_HOST) or ".." in href or urlsplit(href).query:
        raise AcquisitionError("Unexpected Sentinel-2 asset host")
    return href


class RangeSession:
    """Verified HTTPS byte ranges of reviewed COG assets under explicit byte budgets.

    GDAL reads through a Python file object, so no GDAL network driver, credential or
    environment proxy is involved. ``transport`` enables network-free tests.
    """

    def __init__(self, *, transport=None, max_session_bytes=MAX_SESSION_BYTES):
        self.transferred = 0
        self.max_session_bytes = max_session_bytes
        # GDAL reopens a file and reads a few bytes at a time: fetched blocks and asset
        # lengths are kept for the session so each byte crosses the network once.
        self._lengths, self._blocks = {}, {}
        self._client = httpx.Client(
            transport=transport,
            verify=ssl.create_default_context(),
            follow_redirects=False,
            trust_env=False,
            timeout=httpx.Timeout(connect=15, read=45, write=15, pool=15),
            headers={
                "User-Agent": "PropertyPlatform/0.1 (scheduled source acquisition)",
                "Accept-Encoding": "identity",
            },
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._client.close()

    def open(self, href):
        return RangeReader(self, _asset_url(href))

    def _length(self, url):
        if url not in self._lengths:
            response = self._request("HEAD", url)
            try:
                length = int(response.headers["Content-Length"])
            except (KeyError, ValueError) as exc:
                raise AcquisitionError("Sentinel-2 asset has no length") from exc
            if response.status_code != 200 or length <= 0:
                raise AcquisitionError("Sentinel-2 asset is unavailable")
            self._lengths[url] = length
        return self._lengths[url]

    def _request(self, method, url, **headers):
        try:
            response = self._client.request(method, url, headers=headers)
        except httpx.HTTPError as exc:
            raise AcquisitionError(f"Source transport failed: {type(exc).__name__}") from exc
        return response


class RangeReader(io.RawIOBase):
    """Seekable read-only view of one COG, fetched in aligned RANGE_BLOCK ranges.

    GDAL calls this object from C: a Python exception raised there aborts the whole
    process. A failed request is therefore kept in ``error`` and read as end of file;
    ``read_window`` raises it once GDAL has returned.
    """

    def __init__(self, session, url):
        super().__init__()
        self.session, self.url, self.position, self.transferred = session, url, 0, 0
        self.error, self.length = None, 0
        try:
            self.length = session._length(url)
        except AcquisitionError as exc:
            self.error = exc

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.position, io.SEEK_END: self.length}[whence]
        if base + offset < 0:
            raise ValueError("Negative seek position")
        self.position = base + offset
        return self.position

    def read(self, size=-1):
        if self.error is not None:
            return b""
        try:
            return self._read(size)
        except AcquisitionError as exc:
            self.error = exc
            return b""

    def _read(self, size):
        size = min(self.length - self.position, size if size >= 0 else self.length)
        if size <= 0:
            return b""
        start = self.position
        first, last = start // RANGE_BLOCK, (start + size - 1) // RANGE_BLOCK
        blocks = self.session._blocks.setdefault(self.url, {})
        missing = [index for index in range(first, last + 1) if index not in blocks]
        # One request per run of consecutive missing blocks.
        while missing:
            run = 1
            while run < len(missing) and missing[run] == missing[0] + run:
                run += 1
            self._fetch(missing[0], run, blocks)
            missing = missing[run:]
        value = b"".join(blocks[index] for index in range(first, last + 1))
        offset = start - first * RANGE_BLOCK
        self.position += size
        return value[offset : offset + size]

    def _fetch(self, first, count, blocks):
        start = first * RANGE_BLOCK
        size = min(count * RANGE_BLOCK, self.length - start)
        if (
            size > MAX_RANGE_BYTES
            or self.transferred + size > MAX_ASSET_BYTES
            or self.session.transferred + size > self.session.max_session_bytes
        ):
            raise AcquisitionError("Sentinel-2 range budget exceeded")
        response = self.session._request("GET", self.url, Range=f"bytes={start}-{start + size - 1}")
        if response.status_code != 206:
            raise AcquisitionError("Sentinel-2 asset must serve bounded byte ranges")
        if response.headers.get("Content-Encoding", "identity").strip().lower() != "identity":
            raise AcquisitionError("Sentinel-2 asset did not honor the identity encoding")
        value = response.content
        if len(value) != size:
            raise AcquisitionError("Incomplete Sentinel-2 byte range")
        self.transferred += size
        self.session.transferred += size
        for index in range(count):
            blocks[first + index] = value[index * RANGE_BLOCK : (index + 1) * RANGE_BLOCK]

    def readinto(self, buffer):
        value = self.read(len(buffer))
        buffer[: len(value)] = value
        return len(value)


def read_window(scene, geometry, *, open_asset):
    """Read the parcel window of one selected scene on the 10 m grid of its red band.

    ``geometry`` is the parcel as a WGS84 GeoJSON geometry; ``open_asset`` returns a
    binary file object for a reviewed asset href. Returns the encodable window: CRS,
    transform, original digital numbers of each band and the SCL resampled to the 10 m
    grid by nearest neighbour. Raises WindowError when the parcel is outside the tile
    or larger than MAX_WINDOW_PIXELS a side.
    """
    import rasterio

    started = datetime.now(UTC)
    arrays, readers = {}, []

    def opened(key):
        href = scene["assets"][key]["href"]
        # Opened before GDAL so that an unreviewed href raises here, in Python.
        pending = [open_asset(href)]

        # GDAL reads on demand through the opener, never the whole file at once.
        def opener(path, mode="rb"):
            if path != f"{key}.tif" or mode != "rb":
                raise FileNotFoundError(path)
            stream = pending.pop() if pending else open_asset(href)
            readers.append(stream)
            return stream

        return rasterio.open(f"{key}.tif", opener=opener)

    def failure():
        return next((reader.error for reader in readers if getattr(reader, "error", None)), None)

    try:
        crs, transform, width, height = _extract(geometry, opened, arrays)
    except WindowError, AcquisitionError:
        raise
    except Exception as exc:
        if failure() is not None:
            raise failure() from exc
        raise WindowError("Sentinel-2 window could not be read") from exc
    if failure() is not None:
        raise failure()
    return {
        "format": WINDOW_FORMAT,
        "scene_id": scene["scene_id"],
        "tile": scene["tile"],
        "acquired_at": scene["acquired_at"].isoformat(),
        "crs": crs.to_wkt(),
        "transform": [float(value) for value in transform[:6]],
        "width": width,
        "height": height,
        "assets": {
            key: {
                "href": scene["assets"][key]["href"],
                "scale": scene["assets"][key]["scale"],
                "offset": scene["assets"][key]["offset"],
            }
            for key in (*BANDS, CLASSIFICATION)
        },
        "arrays": arrays,
        "fetched_started_at": started,
        "fetched_at": datetime.now(UTC),
        "transferred_bytes": sum(getattr(reader, "transferred", 0) for reader in readers),
        "item_url": ITEM_URL + scene["scene_id"],
    }


def _extract(geometry, opened, arrays):
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT
    from rasterio.warp import transform_geom
    from rasterio.windows import Window

    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_NUM_THREADS="1"):
        with opened("red") as grid:
            projected = transform_geom("EPSG:4326", grid.crs, geometry)
            west, south, east, north = _bounds(projected)
            inverse = ~grid.transform
            cols, rows = zip(
                *(inverse @ point for point in ((west, north), (east, south))), strict=True
            )
            # Reprojection round trips leave ~1e-9 px; do not widen the window for it.
            col_off = math.floor(min(cols) + PIXEL_TOLERANCE)
            row_off = math.floor(min(rows) + PIXEL_TOLERANCE)
            width = math.ceil(max(cols) - PIXEL_TOLERANCE) - col_off
            height = math.ceil(max(rows) - PIXEL_TOLERANCE) - row_off
            if (
                col_off < 0
                or row_off < 0
                or col_off + width > grid.width
                or row_off + height > grid.height
            ):
                raise WindowError("Parcel is not inside this Sentinel-2 tile")
            if not 0 < width <= MAX_WINDOW_PIXELS or not 0 < height <= MAX_WINDOW_PIXELS:
                raise WindowError("Parcel window exceeds the reviewed size")
            window = Window(col_off, row_off, width, height)
            crs, grid_transform = grid.crs, grid.transform
            transform = grid.window_transform(window)
            arrays["red"] = grid.read(1, window=window)
        for key in BANDS:
            if key == "red":
                continue
            with opened(key) as band:
                if band.crs != crs or band.transform != grid_transform:
                    raise WindowError("Sentinel-2 bands do not share one 10 m grid")
                arrays[key] = band.read(1, window=window)
        with (
            opened(CLASSIFICATION) as classification,
            WarpedVRT(
                classification,
                crs=crs,
                transform=transform,
                width=width,
                height=height,
                resampling=Resampling.nearest,
                nodata=0,
            ) as aligned,
        ):
            if classification.crs != crs:
                raise WindowError("Sentinel-2 classification is on another projection")
            arrays[CLASSIFICATION] = aligned.read(1)
    return crs, transform, width, height


def _bounds(geometry):
    points = np.asarray(list(_coordinates(geometry["coordinates"])), dtype=np.float64)
    if points.size == 0 or not np.isfinite(points).all():
        raise WindowError("Parcel geometry has no finite coordinates")
    return (*points.min(axis=0)[:2], *points.max(axis=0)[:2])


def _coordinates(value):
    if value and isinstance(value[0], (int, float)):
        yield value
        return
    for item in value:
        yield from _coordinates(item)


def encode_window(window):
    """Deterministic JSON bytes of a window: metadata and little-endian digital numbers."""
    arrays = {}
    for key in (*BANDS, CLASSIFICATION):
        array = np.asarray(window["arrays"][key])
        dtype = "uint8" if key == CLASSIFICATION else "uint16"
        if array.shape != (window["height"], window["width"]) or not np.can_cast(
            array.dtype, _DTYPES[dtype]
        ):
            raise WindowError("Unexpected Sentinel-2 window array")
        arrays[key] = {
            "dtype": dtype,
            "data": base64.b64encode(array.astype(_DTYPES[dtype]).tobytes()).decode("ascii"),
        }
    document = {
        key: window[key]
        for key in (
            "format",
            "scene_id",
            "tile",
            "acquired_at",
            "crs",
            "transform",
            "width",
            "height",
            "assets",
        )
    }
    document["arrays"] = arrays
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


def decode_window(payload):
    """Rebuild a captured window: reflectance per band, SCL and its grid, or WindowError."""
    try:
        document = json.loads(payload)
        if document["format"] != WINDOW_FORMAT:
            raise WindowError("Unknown Sentinel-2 window format")
        shape = (int(document["height"]), int(document["width"]))
        if not all(0 < size <= MAX_WINDOW_PIXELS for size in shape):
            raise WindowError("Unexpected Sentinel-2 window size")
        transform = [float(value) for value in document["transform"]]
        if len(transform) != 6:
            raise WindowError("Unexpected Sentinel-2 window transform")
        values = {}
        for key in (*BANDS, CLASSIFICATION):
            entry = document["arrays"][key]
            dtype = _DTYPES[entry["dtype"]]
            if (key == CLASSIFICATION) != (entry["dtype"] == "uint8"):
                raise WindowError("Unexpected Sentinel-2 window type")
            raw = base64.b64decode(entry["data"], validate=True)
            if len(raw) != shape[0] * shape[1] * dtype.itemsize:
                raise WindowError("Truncated Sentinel-2 window")
            array = np.frombuffer(raw, dtype=dtype).reshape(shape)
            if key == CLASSIFICATION:
                values[key] = array.astype(np.uint8)
            else:
                asset = document["assets"][key]
                values[key] = reflectance(
                    array, scale=float(asset["scale"]), offset=float(asset["offset"])
                )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, WindowError):
            raise
        raise WindowError("Malformed Sentinel-2 window capture") from exc
    return {
        "scene_id": document["scene_id"],
        "tile": document["tile"],
        "crs": document["crs"],
        "transform": transform,
        "shape": shape,
        "values": values,
    }


def parcel_mask(geometry, window):
    """Pixels of a decoded window whose centre lies in the WGS84 parcel geometry."""
    from affine import Affine
    from rasterio.crs import CRS
    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom

    projected = transform_geom("EPSG:4326", CRS.from_wkt(window["crs"]), geometry)
    return geometry_mask(
        [projected],
        out_shape=window["shape"],
        transform=Affine(*window["transform"]),
        invert=True,
    )
