"""Reviewed AD-SDI parcel publication; independent of Onwani's richer schema."""

import json
import math
import re
from functools import cache
from importlib.resources import files

from ..collection_profiles import COLLECTIONS, collection_for
from . import onwani
from .onwani import SourceError, decode  # noqa: F401

URL = "https://arcgis.sdi.abudhabi.ae/agspublish/rest/services/Pub/Generic_Search_WM/MapServer/10"
VERSION = "adsdi-plots-v1"
FIELDS = (
    "OBJECTID,PLOTID,PLOTNUMBER,DISTRICTENG,COMMUNITYENG,MUNICIPALITYENG,"
    "PRIMARYUSEENG,PRIMARYUSEARA,SOURCEOFORIGIN"
)
MAX_BYTES = 8 * 1024 * 1024
# A district, not an island: Madinat Al Riyad listed 35 077 plots on 27/10/2026, above
# the Onwani island bound. The bound still refuses a listing no reviewed district needs.
MAX_RECORDS = 50000
# One district acquisition: metadata, two listings and every batch of 100. Rural plots are
# large: Al Faqa' sent 66.5 MB in 60 of its 74 batches on 27/10/2026, above the 64 MiB
# session budget shared by other sources.
MAX_RESPONSES = MAX_RECORDS // 100 + 3
MAX_SESSION_BYTES = 256 * 1024 * 1024
MUNICIPALITIES = ("ADM", "AAM", "WRM")
_SCOPE = re.compile(r"(adm|aam|wrm):[a-z0-9]+(?:-[a-z0-9]+)*")
_DISTRICT = re.compile(r"[A-Z0-9'`][A-Z0-9 '`-]{0,79}")


@cache
def district_scopes():
    """Reviewed AD-SDI districts of the emirate; island scopes keep their territory identity."""
    raw = files(__package__).joinpath("sdi_districts.json").read_text(encoding="utf-8")
    result = {}
    for row in json.loads(raw)["districts"]:
        scope, municipality, district = row["scope"], row["municipality"], row["district"]
        territory = scope if scope in COLLECTIONS else None
        if (
            municipality not in MUNICIPALITIES
            or not _DISTRICT.fullmatch(district)
            or (territory is None and not _SCOPE.fullmatch(scope))
            or (territory is None and not scope.startswith(municipality.lower() + ":"))
            or (territory is not None and collection_for(territory).district_name != district)
            or scope in result
        ):
            raise ValueError("Invalid reviewed AD-SDI district registry entry")
        result[scope] = (municipality, district)
    return result


def scope_for(scope):
    try:
        return district_scopes()[scope]
    except (KeyError, TypeError) as exc:
        raise ValueError("Unregistered AD-SDI district scope") from exc


def scopes_in(municipality):
    if municipality not in MUNICIPALITIES:
        raise ValueError("Unknown Abu Dhabi municipality")
    return [scope for scope, row in district_scopes().items() if row[0] == municipality]


def namespace(scope):
    if scope in COLLECTIONS:
        return f"ad-sdi:generic-search:plots:{collection_for(scope).slug}"
    scope_for(scope)
    return f"ad-sdi:generic-search:plots:{scope}"


def where(scope):
    # Island scopes keep their original clause so archived captures replay unchanged.
    if scope in COLLECTIONS:
        return f"UPPER(DISTRICTENG)='{collection_for(scope).district_name}'"
    municipality, district = scope_for(scope)
    quoted = district.replace("'", "''")
    return f"MUNICIPALITYENG='{municipality}' AND DISTRICTENG='{quoted}'"


def object_ids(data):
    return onwani.object_ids(data, MAX_RECORDS)


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


def parse(feature, scope, uses):
    attrs = feature.get("attributes", {})
    municipality, district = scope_for(scope)
    if attrs.get("DISTRICTENG") != district:
        raise SourceError("AD-SDI record outside requested district")
    if attrs.get("MUNICIPALITYENG") != municipality:
        raise SourceError("AD-SDI record outside requested municipality")
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
            "municipality": municipality,
            "district": attrs["DISTRICTENG"],
            "community": attrs.get("COMMUNITYENG") or "",
            "land_use": uses.get(attrs.get("PRIMARYUSEENG"), ""),
            "construction_status": "",
        },
    }
