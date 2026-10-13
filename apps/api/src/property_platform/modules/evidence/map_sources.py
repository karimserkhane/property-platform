"""Fixed public endpoints, bounded captures, no scraping from a browser or HTML dump."""

import json
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .collection_profiles import collection_for
from .onwani import SourceError

VERSION = "district-map-v4"
MAX_BYTES = 16 * 1024 * 1024
OSM_URL = "https://overpass-api.de/api/interpreter"
OSM_MIRROR = "https://overpass.private.coffee/api/interpreter"

# Backward-compatible default protocol constants, generated from one reviewed profile.
OSM_QUERY = collection_for().osm_query
LAYERS = collection_for().map_layers()


def fetch_url(base, params):
    url = base + "?" + urlencode(params)
    started = datetime.now(UTC)
    request = Request(url, headers={"User-Agent": "PropertyPlatform/0.1 (manual map acquisition)"})
    try:
        response = urlopen(request, timeout=60)
    except HTTPError as exc:
        response = exc
    with response:
        payload = response.read(MAX_BYTES + 1)
        receipt = {
            "url": url,
            "fetched_started_at": started,
            "fetched_at": datetime.now(UTC),
            "http_status": response.status,
            "etag": response.headers.get("ETag", "")[:500],
            "last_modified_raw": response.headers.get("Last-Modified", "")[:160],
        }
    if len(payload) > MAX_BYTES:
        raise SourceError("Map capture exceeds size limit")
    return payload, receipt


def decode(payload):
    try:
        value = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as exc:
        raise SourceError("Invalid map response") from exc
    if (
        not isinstance(value, dict)
        or "error" in value
        or value.get("remark")
        or value.get("exceededTransferLimit")
    ):
        raise SourceError("Map source error or truncated response")
    return value


def text(value, limit=255):
    if value is None:
        return ""
    if not isinstance(value, str) or len(value) > limit:
        raise SourceError("Unexpected map text")
    return value.strip()


def coordinates(points, *, closed=False):
    import math

    if not isinstance(points, list) or len(points) < (4 if closed else 2):
        raise SourceError("Incomplete map geometry")
    for p in points:
        if (
            not isinstance(p, (list, tuple))
            or len(p) != 2
            or any(type(n) not in (float, int) or not math.isfinite(n) for n in p)
            or not (54.30 <= p[0] <= 54.55 and 24.40 <= p[1] <= 24.65)
        ):
            raise SourceError("Map geometry outside acquisition envelope")
    if closed and points[0] != points[-1]:
        raise SourceError("Unclosed map ring")
    return points
