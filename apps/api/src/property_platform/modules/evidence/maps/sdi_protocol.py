"""Reviewed AD-SDI parcel publication; independent of Onwani's richer schema."""

import math

from ..collection_profiles import collection_for
from .onwani import SourceError, decode, object_ids  # noqa: F401

URL = "https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/Pub/Generic_Search_WM/MapServer/10"
VERSION = "adsdi-plots-v1"
FIELDS = (
    "OBJECTID,PLOTID,PLOTNUMBER,DISTRICTENG,COMMUNITYENG,MUNICIPALITYENG,"
    "PRIMARYUSEENG,PRIMARYUSEARA,SOURCEOFORIGIN"
)
MAX_BYTES = 8 * 1024 * 1024


def namespace(territory):
    return f"ad-sdi:generic-search:plots:{collection_for(territory).slug}"


def where(territory):
    return f"UPPER(DISTRICTENG)='{collection_for(territory).district_name}'"


def metadata(data):
    if (
        data.get("name") != "Plots"
        or data.get("geometryType") != "esriGeometryPolygon"
        or data.get("extent", {}).get("spatialReference", {}).get("wkid") != 4326
        or data.get("typeIdField") != "PRIMARYUSEENG"
        or not set(FIELDS.split(",")).issubset({f["name"] for f in data.get("fields", [])})
    ):
        raise SourceError("Unexpected AD-SDI parcel schema or CRS")
    uses = {item["id"]: item["name"] for item in data.get("types", [])}
    if uses.get(2) != "Commercial" or uses.get(13) != "Residential":
        raise SourceError("AD-SDI subtype dictionary changed")
    return uses


def parse(feature, territory, uses):
    attrs = feature.get("attributes", {})
    if attrs.get("DISTRICTENG") != collection_for(territory).district_name:
        raise SourceError("AD-SDI record outside requested district")
    if attrs.get("MUNICIPALITYENG") != "ADM":
        raise SourceError("AD-SDI record outside Abu Dhabi municipality")
    oid, plot = attrs.get("OBJECTID"), attrs.get("PLOTID")
    if type(oid) is not int or oid <= 0 or not isinstance(plot, str) or not plot.strip():
        raise SourceError("Missing AD-SDI record or plot identity")
    for key, limit in (("PLOTID", 80), ("PLOTNUMBER", 100), ("COMMUNITYENG", 55)):
        if not isinstance(attrs.get(key) or "", str) or len(attrs.get(key) or "") > limit:
            raise SourceError("Unexpected AD-SDI attribute")
    rings = feature.get("geometry", {}).get("rings")
    if not isinstance(rings, list) or not rings:
        raise SourceError("Missing AD-SDI polygon")
    for ring in rings:
        if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
            raise SourceError("Unclosed AD-SDI polygon")
        for point in ring:
            if (
                not isinstance(point, list)
                or len(point) != 2
                or any(type(n) not in (int, float) or not math.isfinite(n) for n in point)
                or not -180 <= point[0] <= 180
                or not -90 <= point[1] <= 90
            ):
                raise SourceError("Invalid AD-SDI WGS84 coordinate")
    return {
        "record_id": plot,
        "attributes": attrs,
        "rings": rings,
        "values": {
            "official_plot_id": plot,
            "code": " / ".join(filter(None, [attrs.get("COMMUNITYENG"), attrs.get("PLOTNUMBER")])),
            "municipality": "ADM",
            "district": attrs["DISTRICTENG"],
            "community": attrs.get("COMMUNITYENG") or "",
            "land_use": uses.get(attrs.get("PRIMARYUSEENG"), ""),
            "construction_status": "",
        },
    }
