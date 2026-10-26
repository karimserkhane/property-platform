"""Reviewed public context feeds. Parsing is inert; no ORM or arbitrary URLs."""

import base64
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import urlencode

VERSION = "abu-dhabi-public-context-v1"
MAX_BYTES = 4 * 1024 * 1024
MAX_ROWS = 5000
DISTRICT_BASE = "https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/1/query"
DISTRICT_IDS = (
    DISTRICT_BASE + "?" + urlencode({"f": "json", "where": "1=1", "returnIdsOnly": "true"})
)
DISTRICT_GEOJSON = (
    DISTRICT_BASE
    + "?"
    + urlencode(
        {
            "f": "geojson",
            "where": "1=1",
            "outFields": "OBJECTID,DISTRICTID,NAMEENGLISH,NAMEARABIC,MUNICIPALITYNAME",
            "outSR": "4326",
            "returnGeometry": "true",
        }
    )
)


@dataclass(frozen=True)
class Feed:
    key: str
    name: str
    url: str
    page_url: str
    # Public access does not imply a commercial redistribution licence.
    reuse_status: str = "public_access_license_unconfirmed"


FEEDS = {
    "districts": Feed(
        "dmt:onwani:emirate:districts",
        "DMT / Onwani — Abu Dhabi districts",
        DISTRICT_GEOJSON,
        "https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/1",
    ),
    "health": Feed(
        "doh:publicmap:facilities",
        "DoH — public health facility map",
        "https://stem.doh.gov.ae/HFMap/Home/GetAllFacilities",
        "https://stem.doh.gov.ae/publicmap/",
    ),
    "schools": Feed(
        "adek:charter:schools",
        "ADEK — Charter schools",
        "https://charterschools.abudhabi/documents/d/charterschools/schools",
        "https://charterschools.abudhabi/find-a-school",
    ),
    "mobility": Feed(
        "admobility:bus:routes",
        "Abu Dhabi Mobility — bus routes",
        "https://admobility.gov.ae/en/pb-bus-service/",
        "https://admobility.gov.ae/en/pb-bus-service/",
    ),
    "statistics": Feed(
        "scad:census:real-estate",
        "SCAD — real estate census",
        "https://census.scad.gov.ae/home/realestate?lang=en&tab=tool_interactive_unit",
        "https://census.scad.gov.ae/home/realestate?lang=en",
    ),
}


class ContextError(ValueError):
    pass


def archive_response(scope, row):
    """Operator-supplied original public document; never fabricate a fresh HTTP fetch."""
    if scope != "abu-dhabi:schools" or not isinstance(row, dict):
        raise ContextError("Only the reviewed school archive is supported")
    fields = {
        "scope",
        "url",
        "payload_base64",
        "sha256",
        "http_status",
        "fetched_at",
        "timestamp_basis",
        "acquisition_method",
    }
    if set(row) != fields or row["scope"] != scope or row["url"] != feed_for(scope).url:
        raise ContextError("Archive does not identify the registered school document")
    if (
        row["http_status"] != 200
        or row["timestamp_basis"] != "artifact_filesystem_time"
        or row["acquisition_method"] != "manual_archive_import"
        or not isinstance(row["payload_base64"], str)
        or len(row["payload_base64"]) > (MAX_BYTES + 2) // 3 * 4
    ):
        raise ContextError("Invalid archive provenance or byte budget")
    try:
        payload = base64.b64decode(row["payload_base64"], validate=True)
        fetched = datetime.fromisoformat(row["fetched_at"])
    except (TypeError, ValueError) as exc:
        raise ContextError("Invalid archive encoding or timestamp") from exc
    if (
        not fetched.tzinfo
        or fetched > datetime.now(UTC)
        or not payload
        or len(payload) > MAX_BYTES
        or hashlib.sha256(payload).hexdigest() != row["sha256"]
    ):
        raise ContextError("Archive hash or timestamp differs from its declaration")
    return payload, {
        "url": row["url"],
        "fetched_started_at": None,
        "fetched_at": fetched,
        "http_status": 200,
        "etag": "",
        "last_modified_raw": "",
        "timestamp_basis": row["timestamp_basis"],
        "acquisition_method": row["acquisition_method"],
    }


def feed_for(scope):
    if scope not in {f"abu-dhabi:{key}" for key in FEEDS}:
        raise ContextError("Unregistered public context scope")
    return FEEDS[scope.split(":")[1]]


def source_definition(operation, scope):
    if operation != "public_context":
        raise ContextError("Unknown context operation")
    feed = feed_for(scope)
    return feed.key, feed.name, feed.page_url, VERSION


def validate_request(scope, url, params):
    if url not in urls_for(scope) or params:
        raise ContextError("Context request differs from its registered feed")


def urls_for(scope):
    feed = feed_for(scope)
    return [feed.url, DISTRICT_IDS] if scope == "abu-dhabi:districts" else [feed.url]


def district_ids(payload):
    data = decode(payload)
    ids = data.get("objectIds") if isinstance(data, dict) else None
    if (
        not isinstance(ids, list)
        or not 1 <= len(ids) <= MAX_ROWS
        or any(type(i) is not int or not 0 < i <= 2**63 - 1 for i in ids)
        or len(set(ids)) != len(ids)
        or data.get("error")
    ):
        raise ContextError("District identity listing invalid or incomplete")
    return set(map(str, ids))


def collect(scope, acquire):
    feed = feed_for(scope)
    before = district_ids(acquire(DISTRICT_IDS, {})[0]) if scope == "abu-dhabi:districts" else None
    payload, capture = acquire(feed.url, {})
    rows, modified = parse(scope, payload)
    if before is not None:
        after = district_ids(acquire(DISTRICT_IDS, {})[0])
        if before != after or before != {row[2]["source_record_id"] for row in rows}:
            raise ContextError("District snapshot missing identities or changed during collection")
    return capture, rows, modified


def text(value, maximum=255, *, required=False):
    if value is None and not required:
        return ""
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise ContextError("Invalid source text")
    return value.strip()


def digest(row):
    return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def decode(payload):
    if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_BYTES:
        raise ContextError("Context response exceeds budget or is empty")
    try:
        return json.loads(
            payload,
            parse_constant=lambda _: (_ for _ in ()).throw(ContextError("Non-finite source value")),
        )
    except (ValueError, UnicodeError) as exc:
        raise ContextError("Invalid public source JSON") from exc


def coordinate(longitude, latitude):
    if (
        type(longitude) not in (int, float)
        or type(latitude) not in (int, float)
        or not math.isfinite(longitude)
        or not math.isfinite(latitude)
        or not 51 <= longitude <= 56.3
        or not 22.4 <= latitude <= 25.3
    ):
        raise ContextError("Missing or out-of-scope Abu Dhabi coordinates")
    return longitude, latitude


class SourceHTML(HTMLParser):
    """Read only the published route select and structured data scripts."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.routes, self.scripts = [], []
        self.select, self.option, self.script = False, None, None
        self.route_selects = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "select" and values.get("id") == "drpBusRoutes":
            self.select = True
            self.route_selects += 1
        if tag == "option" and self.select:
            self.option = (values, [])
        if tag == "script" and values.get("type") == "application/ld+json":
            self.script = []

    def handle_data(self, value):
        if self.option is not None:
            self.option[1].append(value)
        if self.script is not None:
            self.script.append(value)

    def handle_endtag(self, tag):
        if tag == "option" and self.option is not None:
            attrs, parts = self.option
            if attrs.get("value"):
                self.routes.append({**attrs, "label": "".join(parts).strip()})
            self.option = None
        if tag == "select":
            self.select = False
        if tag == "script" and self.script is not None:
            self.scripts.append("".join(self.script))
            self.script = None


def health_rows(payload):
    rows = decode(payload)
    if not isinstance(rows, list):
        raise ContextError("Expected public facility array")
    output = []
    for i, row in enumerate(rows):
        if (
            not isinstance(row, dict)
            or type(row.get("FacilityID")) is not int
            or row["FacilityID"] <= 0
        ):
            raise ContextError("Invalid facility identity")
        if type(row.get("IsPlannedProperty")) is not bool:
            raise ContextError("Facility planned status must be known")
        lon, lat = coordinate(row.get("Longitude"), row.get("Latitude"))
        output.append(
            (
                f"[{i}]",
                row,
                {
                    "source_record_id": str(row["FacilityID"]),
                    "name": text(row.get("FacilityName"), required=True),
                    "facility_type": text(row.get("FacilityType"), required=True),
                    "address": text(row.get("Address"), 2000),
                    "planned": row["IsPlannedProperty"],
                    "operator": text(row.get("FacilityOwnership")),
                    "licence_number": text(row.get("LicenceNumber")),
                    "services_original": text(row.get("ClinicalServices"), 20000),
                    "longitude": lon,
                    "latitude": lat,
                },
            )
        )
    return output, None


def school_rows(payload):
    data = decode(payload)
    if (
        not isinstance(data, dict)
        or data.get("type") != "FeatureCollection"
        or not isinstance(data.get("features"), list)
    ):
        raise ContextError("Expected Charter school GeoJSON")
    output = []
    for i, row in enumerate(data["features"]):
        props, geo = row.get("properties"), row.get("geometry")
        if not isinstance(props, dict) or not isinstance(geo, dict) or geo.get("type") != "Point":
            raise ContextError("Expected school properties and point")
        if props.get("SCH_EDUCATION_TYPE_DESC") != "Charter":
            raise ContextError("School category is not Charter")
        coords = geo.get("coordinates")
        if not isinstance(coords, list) or len(coords) != 2:
            raise ContextError("School coordinates missing")
        lon, lat = coordinate(*coords)
        identity = text(props.get("SCH_ESIS_ID"), 80, required=True)
        if not identity.isascii() or not identity.isdecimal():
            raise ContextError("Invalid ESIS identity")
        output.append(
            (
                f"features[{i}]",
                row,
                {
                    "source_record_id": identity,
                    "name": text(props.get("SCH_NAME_EN"), required=True),
                    "name_ar": text(props.get("SCH_NAME_AR")),
                    "municipality": text(props.get("SCH_MUNICIPALITY_EN"), required=True),
                    "district": text(props.get("SCH_DISTRICT_EN")),
                    "district_ar": text(props.get("SCH_DISTRICT_AR")),
                    "community": text(props.get("SCH_COMMUNITY_EN")),
                    "grades_original": text(props.get("SCH_GRADES_ALL")),
                    "longitude": lon,
                    "latitude": lat,
                },
            )
        )
    return output, None


def district_rows(payload):
    data = decode(payload)
    if (
        not isinstance(data, dict)
        or data.get("type") != "FeatureCollection"
        or not isinstance(data.get("features"), list)
        or data.get("exceededTransferLimit")
        or data.get("crs")
        or data.get("error")
    ):
        raise ContextError("District GeoJSON incomplete or unexpected CRS")
    output = []
    for i, row in enumerate(data["features"]):
        attrs, geo = row.get("properties"), row.get("geometry")
        if not isinstance(attrs, dict) or not isinstance(geo, dict):
            raise ContextError("District properties or geometry missing")
        oid, identity = attrs.get("OBJECTID"), attrs.get("DISTRICTID")
        if (
            type(oid) is not int
            or oid <= 0
            or row.get("id") != oid
            or type(identity) is not int
            or identity <= 0
            or attrs.get("MUNICIPALITYNAME") not in {"ADM", "AAM", "WRM"}
        ):
            raise ContextError("District identity or municipality unknown")
        polygons = geo.get("coordinates")
        if geo.get("type") == "Polygon":
            polygons = [polygons]
        elif geo.get("type") != "MultiPolygon":
            raise ContextError("District must have polygon boundaries")
        if not isinstance(polygons, list) or not polygons:
            raise ContextError("Empty district boundary")
        for polygon in polygons:
            if not isinstance(polygon, list) or not polygon:
                raise ContextError("District rings missing")
            for ring in polygon:
                if (
                    not isinstance(ring, list)
                    or not 4 <= len(ring) <= 100000
                    or ring[0] != ring[-1]
                ):
                    raise ContextError("District ring incomplete")
                for point in ring:
                    if (
                        not isinstance(point, list)
                        or len(point) != 2
                        or any(type(n) not in (int, float) or not math.isfinite(n) for n in point)
                        or not 51 <= point[0] <= 56.3
                        or not 22 <= point[1] <= 26
                    ):
                        raise ContextError("District coordinates outside reviewed envelope")
        output.append(
            (
                f"features[{i}]",
                row,
                {
                    "source_record_id": str(oid),
                    "district_id": identity,
                    "name": text(attrs.get("NAMEENGLISH"), required=True),
                    "name_ar": text(attrs.get("NAMEARABIC")),
                    "municipality": attrs["MUNICIPALITYNAME"],
                    "geometry": geo,
                },
            )
        )
    return output, None


def mobility_rows(parser):
    if parser.route_selects != 1:
        raise ContextError("Published route select missing or duplicated")
    output = []
    for i, row in enumerate(parser.routes):
        identity = text(row.get("value"), 80, required=True)
        if not re.fullmatch(r"auh:[A-Za-z0-9]+:P:H:[A-Za-z0-9]+", identity):
            raise ContextError("Unexpected bus route namespace")
        number = text(row.get("data-busnum"), 20, required=True)
        if not re.fullmatch(r"[A-Za-z0-9]+", number):
            raise ContextError("Invalid public bus number")
        output.append(
            (
                f"select#drpBusRoutes/option[{i}]",
                row,
                {
                    "source_record_id": identity,
                    "number": number,
                    "name": text(row.get("label"), required=True),
                    "origin": text(row.get("data-from"), 500, required=True),
                    "destination": text(row.get("data-to"), 500, required=True),
                    # Published BusRoutes.js constructs this link. PDF contents are not ingested.
                    "timetable_url": f"https://admobility.gov.ae/ckfinder/userfiles/files/BusService{number}.pdf",
                },
            )
        )
    return output, None


def statistics_rows(parser):
    datasets = []
    for script in parser.scripts:
        data = decode(script.encode())
        if isinstance(data, dict):
            datasets.extend(x for x in data.get("@graph", []) if x.get("@type") == "Dataset")
    if len(datasets) != 1:
        raise ContextError("SCAD dataset missing or ambiguous")
    dataset = datasets[0]
    if (
        dataset.get("spatialCoverage", {}).get("name")
        != "Emirate of Abu Dhabi, United Arab Emirates"
        or "rounded to a multiple of 5" not in text(dataset.get("description"), 4000).lower()
    ):
        raise ContextError("Unreviewed SCAD geography or disclosure rounding policy")
    year = dataset.get("temporalCoverage")
    if not isinstance(year, str) or not re.fullmatch(r"20\d{2}", year):
        raise ContextError("SCAD reference year unknown")
    modified = date.fromisoformat(dataset["dateModified"]) if dataset.get("dateModified") else None
    measures = dataset.get("variableMeasured")
    if not isinstance(measures, list):
        raise ContextError("SCAD measures missing")
    output = []
    for i, row in enumerate(measures):
        label = text(row.get("name"), required=True)
        unit = text(row.get("unitText"), 40, required=True)
        value = row.get("value")
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value < 10**12:
            raise ContextError("Invalid SCAD measure")
        if unit not in {"buildings", "units", "percent"} or year not in label:
            raise ContextError("Unreviewed census unit or period")
        is_growth = unit == "percent"
        region = next(
            (r for r in ["Al Ain Region", "Al Dhafra Region", "Abu Dhabi Region"] if r in label),
            "Emirate of Abu Dhabi",
        )
        category = (
            "non_residential"
            if "Non-residential" in label
            else "residential"
            if "Residential" in label
            else "all"
        )
        output.append(
            (
                f"Dataset.variableMeasured[{i}]",
                row,
                {
                    "source_record_id": hashlib.sha256(label.encode()).hexdigest(),
                    "name": label,
                    "reference_year": int(year),
                    "region": region,
                    "category": category,
                    "unit": unit,
                    "value": Decimal(str(value)),
                    "rounding_base": None if is_growth else 5,
                },
            )
        )
    return output, modified


def parse(scope, payload):
    feed_for(scope)
    dataset = scope.split(":")[1]
    if dataset == "health":
        result = health_rows(payload)
    elif dataset == "schools":
        result = school_rows(payload)
    elif dataset == "districts":
        result = district_rows(payload)
    else:
        if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_BYTES:
            raise ContextError("Invalid context HTML size")
        parser = SourceHTML()
        try:
            parser.feed(payload.decode("utf-8-sig"))
        except UnicodeError as exc:
            raise ContextError("Invalid source HTML encoding") from exc
        result = mobility_rows(parser) if dataset == "mobility" else statistics_rows(parser)
    rows, _ = result
    if not 0 < len(rows) <= MAX_ROWS:
        raise ContextError("Empty or excessive context coverage")
    identities = [values["source_record_id"] for _, _, values in rows]
    if len(set(identities)) != len(identities):
        raise ContextError("Duplicate source identities in a snapshot")
    return result
