"""Public read-only connector; no Django/GIS imports so protocol tests stay portable."""

import json
import math
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..collection_profiles import DEFAULT_TERRITORY, collection_for

SOURCE_KEY = collection_for().parcel_namespace
BASE_URL = "https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/0"
VERSION = "onwani-district-v4"
WHERE = collection_for().parcel_where
FIELDS = (
    "OBJECTID,PLOTID,GISID,SectorNumber_PlotID,DISTRICTENG,DISTRICTID,"
    "MUNICIPALITYENG,COMMUNITYENG,ELMS_LandUse_Const,Construction_Status,"
    "APPROVALDATE,MODIFIEDDATE,DataReceivedDate,Permit_LastDate,Permit_LastType,"
    "MEPS_CONS_STATUS,MEPS_CONS_UPDATEON,DMT_DCR_URL,ELMS_LANDUSENAME_E,"
    "ELMS_LANDUSENAME_A,PLANNINGSTATUS,OWNERSHIPTYPE,ELMS_AllocationStatus,"
    "CALCULATEDAREA,ELMS_PARENTLANDUSE_E"
)
MAX_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 20000


class SourceError(ValueError):
    pass


def fetch(params=None):
    url = BASE_URL + ("/query?" + urlencode({"f": "json", **params}) if params else "?f=pjson")
    started = datetime.now(UTC)
    request = Request(
        url, headers={"User-Agent": "PropertyPlatform/0.1 (manual source acquisition)"}
    )
    try:
        response = urlopen(request, timeout=30)
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
        raise SourceError("Source response exceeds size limit")
    return payload, receipt


def decode(payload):
    try:
        data = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as exc:
        raise SourceError("Source response is not valid JSON") from exc
    if not isinstance(data, dict) or data.get("error") or data.get("exceededTransferLimit"):
        raise SourceError("Source error or truncated response")
    return data


def object_ids(data):
    ids = data.get("objectIds")
    if not isinstance(ids, list) or not ids or len(ids) > MAX_RECORDS:
        raise SourceError("Empty or unexpectedly large territory")
    if any(type(value) is not int or value <= 0 for value in ids) or len(set(ids)) != len(ids):
        raise SourceError("Invalid or duplicate source identities")
    return sorted(ids)


def parse_feature(feature, *, territory=DEFAULT_TERRITORY):
    if not isinstance(feature, dict):
        raise SourceError("Invalid feature")
    attrs = feature.get("attributes")
    if not isinstance(attrs, dict):
        raise SourceError("Missing feature attributes")
    if (
        attrs.get("DISTRICTENG") != collection_for(territory).district_name
        or attrs.get("MUNICIPALITYENG") != "ADM"
    ):
        raise SourceError("Feature outside requested territory")
    oid = attrs.get("OBJECTID")
    if type(oid) is not int or oid <= 0:
        raise SourceError("Missing source identity")
    geometry = feature.get("geometry")
    rings = geometry.get("rings") if isinstance(geometry, dict) else None
    if not isinstance(rings, list) or not rings:
        raise SourceError("Missing polygon geometry")
    for ring in rings:
        if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
            raise SourceError("Unclosed or incomplete polygon ring")
        for point in ring:
            if (
                not isinstance(point, list)
                or len(point) != 2
                or any(type(n) not in (int, float) or not math.isfinite(n) for n in point)
                or not -180 <= point[0] <= 180
                or not -90 <= point[1] <= 90
            ):
                raise SourceError("Invalid WGS84 coordinates")
    mapping = {
        "official_plot_id": ("PLOTID", 80),
        "code": ("SectorNumber_PlotID", 160),
        "municipality": ("MUNICIPALITYENG", 80),
        "district": ("DISTRICTENG", 160),
        "community": ("COMMUNITYENG", 160),
        "land_use": ("ELMS_LandUse_Const", 255),
        "construction_status": ("Construction_Status", 160),
    }
    values = {}
    for name, (field, limit) in mapping.items():
        value = attrs.get(field)
        if value is not None and (not isinstance(value, str) or len(value) > limit):
            raise SourceError("Unexpected attribute type or length")
        values[name] = value or ""
    detailed_use = attrs.get("ELMS_LANDUSENAME_E")
    if detailed_use is not None:
        if not isinstance(detailed_use, str) or len(detailed_use) > 255:
            raise SourceError("Unexpected detailed land use")
        values["land_use"] = detailed_use or values["land_use"]
    return {"record_id": str(oid), "values": values, "rings": rings, "attributes": attrs}


def validate_metadata(data):
    if (
        data.get("name") != "PLOT"
        or data.get("geometryType") != "esriGeometryPolygon"
        or data.get("extent", {}).get("spatialReference", {}).get("wkid") != 4326
    ):
        raise SourceError("Unexpected source layer or CRS")
    fields = {field["name"] for field in data.get("fields", [])}
    if not set(FIELDS.split(",")).issubset(fields):
        raise SourceError("Source schema changed")
