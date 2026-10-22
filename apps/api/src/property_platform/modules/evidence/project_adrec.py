"""Public ADREC project-register facts, distinct from sales or developer marketing."""

import json
import math
import re
from urllib.parse import parse_qs, urlsplit


def _name(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def adrec_record(project, source, payload):
    if type(payload) is not bytes or not 0 < len(payload) <= 4 * 1024 * 1024:
        raise ValueError("ADREC project exceeds its response budget")
    envelope = json.loads(payload)
    record = envelope.get("Data", {}).get("Result") if isinstance(envelope, dict) else None
    url = urlsplit(source["url"])
    if (
        not isinstance(record, dict)
        or envelope.get("Success") is not True
        or url.hostname != "adrec.gov.ae"
        or url.path != "/api/feature/Profession/ProjectDetail"
        or parse_qs(url.query) != {"id": [source["record_id"]]}
        or str(record.get("Id")) != source["record_id"]
        or record.get("ProjectNumber") != source["registration_number"]
        or record.get("MunicipalityId") != 1000
        or record.get("DistrictId") != source["district_id"]
        or record.get("DistrictEn")
        != {"saadiyat-island": "Al Saadiyat Island", "al-reem-island": "Al Reem Island"}.get(
            project["territory_id"]
        )
        or _name(record.get("Name") or "")
        not in {_name(value) for value in source["heading_aliases"]}
        or _name(record.get("DeveloperName") or "")
        not in {_name(value) for value in source["developer_aliases"]}
    ):
        raise ValueError("ADREC project registration, party or territory changed")
    return record


def adrec_project(project, source, receipt, base):
    record = adrec_record(project, source, receipt["payload"])
    result = base(project, source)
    result["parser_version"] = "adrec-project-register-v1"
    result["title"] = record["Name"].strip()
    result["source_developer_name"] = record["DeveloperName"].strip()
    result["source_developer_role"] = "registered"
    pointer = f"JSON:Data.Result[Id={record['Id']},ProjectNumber={record['ProjectNumber']}]"
    # A component registration may establish identity/types without describing
    # the whole parent programme. Never promote its subtotal or summary to it.
    if source.get("fact_scope") == "project":
        description = record.get("Description")
        if isinstance(description, str):
            from .project_protocol import _Document

            result["summary"] = _Document(description.encode()).root.text()[:450]
        count = record.get("ResidentialUnits")
        if type(count) is int and 0 < count <= 100000:
            result.update(
                total_units=count,
                total_units_basis="registered",
                total_units_original=f"ResidentialUnits: {count}",
                total_units_pointer=pointer + ".ResidentialUnits",
            )
    # EndDate and registration CreateDate have no reviewed handover semantics.
    # UnitCount is frequently zero; listing totalCount can include retail units.
    types = {"APARTMENT": "apartment", "VILLA": "villa", "TOWNHOUSE": "townhouse"}
    bedrooms = {
        "Studio": 0,
        "OneBedroom": 1,
        "TwoBedroom": 2,
        "ThreeBedroom": 3,
        "FourBedroom": 4,
        "FiveBedroom": 5,
        "SixBedroom": 6,
        "SevenBedroom": 7,
        "EightBedroom": 8,
        "NineBedroom": 9,
        "TenBedroom": 10,
        "ElevenBedroom": 11,
        "TwelveBedroom": 12,
        "FifteenBedroom": 15,
    }
    units = record.get("PropertyProjectUnits") or []
    if not isinstance(units, list) or len(units) > 100:
        raise ValueError("ADREC project type breakdown changed")
    seen = set()
    for index, row in enumerate(units):
        if not isinstance(row, dict) or row.get("Type") not in types:
            continue
        kind = types[row["Type"]]
        for key, bed in bedrooms.items():
            count = row.get(key)
            if type(count) is not int or not 0 < count <= 100000 or (kind, bed) in seen:
                continue
            seen.add((kind, bed))
            result["typologies"].append(
                {
                    "property_type": kind,
                    "bedrooms": bed,
                    "original_text": f"{row['Type']}: {key}={count}",
                    "evidence_pointer": f"{pointer}.PropertyProjectUnits[{index}].{key}",
                }
            )
    return result


def adrec_position(project, source, payload):
    record = adrec_record(project, source, payload)
    lat, lon = record.get("Latitude"), record.get("Longitude")
    if source.get("fact_scope") != "project" or any(
        type(value) not in (int, float) or not math.isfinite(value) for value in (lat, lon)
    ):
        return None
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return None
    return {
        "lat": lat,
        "lon": lon,
        "method": "authority_registered_project_coordinates",
        "source_kind": "authority",
        "source_name": "Abu Dhabi Real Estate Centre (ADREC)",
        "evidence_pointer": f"JSON:Data.Result[Id={record['Id']}].Latitude/Longitude",
    }
