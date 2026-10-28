"""PSI public project observations, separated from organization and marketing data.

Only inert JSON embedded in the public page is decoded. No JavaScript execution,
private CRM request, inventory price, promised return or agency-office geocoding.
"""

import json
import math
import re
from datetime import date
from urllib.parse import urlsplit


def _identity(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def psi_record(payload):
    if type(payload) is not bytes or not 0 < len(payload) <= 4 * 1024 * 1024:
        raise ValueError("PSI project exceeds its response budget")
    chunks = []
    for match in re.finditer(
        r"self\.__next_f\.push\((\[.*?\])\)</script>", payload.decode("utf-8"), re.S
    ):
        value = json.loads(match[1])
        if (
            isinstance(value, list)
            and len(value) == 2
            and value[0] == 1
            and isinstance(value[1], str)
        ):
            chunks.append(value[1])
    text, rows = "".join(chunks), []
    decoder = json.JSONDecoder()
    for match in re.finditer(r'"data":(?=\{"propertyId":)', text):
        row, _ = decoder.raw_decode(text, match.end())
        if isinstance(row, dict) and isinstance(row.get("propertyName"), str):
            rows.append(row)
    if len(rows) != 1:
        raise ValueError("PSI project data are absent or ambiguous")
    return rows[0]


def checked_psi_record(project, source, payload):
    row = psi_record(payload)
    territory = {
        "al-reem-island": "Al Reem Island",
        "saadiyat-island": "Saadiyat Island",
        "al-maryah-island": "Al Maryah Island",
    }
    names = [project["name"], *source.get("heading_aliases", [])]
    parts = urlsplit(source["url"])
    if (
        parts.hostname != "psinv.net"
        or str(row.get("propertyId")) != source.get("record_id")
        or not parts.path.endswith("-" + source["record_id"])
        or row.get("community") != territory.get(project["territory_id"])
        or row.get("city") != "Abu Dhabi"
        or _identity(row["propertyName"]) not in {_identity(name) for name in names}
        or _identity(row.get("developerName") or "")
        not in {_identity(name) for name in source.get("developer_aliases", [])}
    ):
        raise ValueError("PSI project identity, developer or territory changed")
    return row


def psi_project(project, source, receipt, base, amenity):
    row = checked_psi_record(project, source, receipt["payload"])
    result = base(project, source)
    result["parser_version"] = "psi-project-v2"
    result["source_developer_name"] = row.get("developerName") or ""
    result["source_developer_role"] = "declared" if result["source_developer_name"] else ""
    pointer = f"PSI public page:data[propertyId={row['propertyId']}]"
    value = row.get("handoverDate")
    if value:
        try:
            parsed = date.fromisoformat(value)
        except (ValueError, TypeError) as exc:
            raise ValueError("PSI handover date changed") from exc
        if not 1900 <= parsed.year <= 2200:
            raise ValueError("PSI handover date is outside the accepted range")
        result["handover"] = {
            "precision": "day",
            "year": parsed.year,
            "month": parsed.month,
            "day": parsed.day,
            "quarter": None,
            "original_text": value,
            "evidence_pointer": pointer + ".handoverDate",
        }
    types = row.get("unitTypes") or []
    bedrooms = row.get("availableBedrooms") or []
    if (
        not isinstance(types, list)
        or len(types) > 30
        or not isinstance(bedrooms, list)
        or len(bedrooms) > 30
    ):
        raise ValueError("PSI residential types changed")
    normalized = {
        "Apartment": "apartment",
        "Villa": "villa",
        "Townhouse": "townhouse",
        "Penthouse": "penthouse",
        "Duplex": "duplex",
        "Studio": "apartment",
    }
    known = list(dict.fromkeys(normalized[value] for value in types if value in normalized))
    # A separate bedroom list cannot establish every type/bedroom combination.
    for kind in known:
        beds = bedrooms if len(known) == 1 and bedrooms else [None]
        for bed in beds:
            if bed is not None and (type(bed) is not int or not 0 <= bed <= 20):
                continue
            result["typologies"].append(
                {
                    "property_type": kind,
                    "bedrooms": bed,
                    "original_text": json.dumps(
                        {"unitTypes": types, "availableBedrooms": bedrooms}
                    ),
                    "evidence_pointer": pointer + ".unitTypes/availableBedrooms",
                }
            )
    for field in ("facilities", "amenities"):
        items = row.get(field) or []
        if not isinstance(items, list) or len(items) > 200:
            raise ValueError("PSI amenities exceed their budget")
        for index, value in enumerate(items):
            if isinstance(value, str) and (item := amenity(value, f"{pointer}.{field}[{index}]")):
                if not any(old["code"] == item["code"] for old in result["amenities"]):
                    result["amenities"].append(item)
    return result


def psi_position(project, source, payload):
    row = checked_psi_record(project, source, payload)
    lat, lon = row.get("latitude"), row.get("longitude")
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in (lat, lon)):
        return None
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return None
    # Reused defaults observed on unrelated projects in the public catalogue;
    # they are island reference points, not evidence for an individual building.
    if (round(lat, 6), round(lon, 6)) in {
        (24.494244, 54.406860),
        (24.530292, 54.445158),
    }:
        return None
    return {
        "lat": lat,
        "lon": lon,
        "method": "broker_project_coordinates",
        "source_kind": "broker",
        "source_name": "Property Shop Investment (PSI)",
        "publisher_key": "psi",
        "evidence_pointer": (
            f"PSI public page:data[propertyId={row['propertyId']}].latitude/longitude"
        ),
    }
