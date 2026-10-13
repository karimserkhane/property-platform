"""Fixed public endpoints, bounded captures, no scraping from a browser or HTML dump."""

import json
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .onwani import SourceError

VERSION = "reem-map-v3"
MAX_BYTES = 16 * 1024 * 1024
OSM_URL = "https://overpass-api.de/api/interpreter"
OSM_MIRROR = "https://overpass.private.coffee/api/interpreter"
OSM_QUERY = (
    "[out:json][timeout:45];("
    "way[building](24.4707,54.3886,24.5177,54.4273);"
    "way[highway][name](24.4707,54.3886,24.5177,54.4273);"
    "nwr[name][amenity](24.4707,54.3886,24.5177,54.4273);"
    "nwr[name][leisure](24.4707,54.3886,24.5177,54.4273);"
    "nwr[name][building](24.4707,54.3886,24.5177,54.4273););out meta center geom;"
)
LAYERS = {
    "district": (
        "https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/1",
        "NAMEENGLISH='AL REEM ISLAND'",
        "esriGeometryPolygon",
        "OBJECTID,NAMEENGLISH,NAMEARABIC,DISTRICTID",
    ),
    "community": (
        "https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/2",
        "DISTRICTID='57' AND UPPER(DISTRICTNAMEENG)='AL REEM ISLAND'",
        "esriGeometryPolygon",
        "OBJECTID,COMMUNITYNAMEENG,COMMUNITYNAMEARA,DISTRICTID",
    ),
    "street": (
        "https://onwani.abudhabi.ae/arcgis/rest/services/Onwani/UDM_AddressingLayers/MapServer/2",
        "UPPER(DISTRICT_EN)='AL REEM ISLAND'",
        "esriGeometryPolyline",
        "OBJECTID,ROADNAME_EN,ROADNAME_AR,NAME_EN,NAME_AR,ROADTYPE_EN,DISTRICT_EN",
    ),
}


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
            or not (54.30 <= p[0] <= 54.55 and 24.40 <= p[1] <= 24.60)
        ):
            raise SourceError("Map geometry outside acquisition envelope")
    if closed and points[0] != points[-1]:
        raise SourceError("Unclosed map ring")
    return points
