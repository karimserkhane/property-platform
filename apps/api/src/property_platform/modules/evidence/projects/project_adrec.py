"""Public ADREC project-register facts, distinct from sales or developer marketing."""

import json
import math
import re
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

REGISTER_TIMEZONE = ZoneInfo("Asia/Dubai")


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
    result["parser_version"] = "adrec-project-register-v2"
    result["title"] = record["Name"].strip()
    result["source_developer_name"] = record["DeveloperName"].strip()
    result["source_developer_role"] = "registered"
    pointer = f"JSON:Data.Result[Id={record['Id']},ProjectNumber={record['ProjectNumber']}]"
    # Verification facts describe the registration itself, whatever its scope.
    result["verification"] = adrec_verification(record, source, pointer)
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


def _text(value, limit):
    """A register string as given (trimmed), or blank when absent or out of bounds."""
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        return ""
    return value.strip()


def _percent(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _register_day(value):
    """`/Date(ms)/` instants and midnight ISO stamps are register days in UAE time."""
    if not isinstance(value, str):
        return None
    if match := re.fullmatch(r"/Date\((\d{1,15})\)/", value):
        return datetime.fromtimestamp(int(match[1]) / 1000, REGISTER_TIMEZONE).date()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}(T00:00:00)?", value):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def adrec_verification(record, source, pointer):
    """Register facts a buyer checks, as published; nothing is derived or completed.

    Sold share is kept only when the register states a percentage: a bare "0" is
    published for projects with no sales report as well, so it stays original text.
    The inspection report is attached only when it matches the headline progress.
    """
    progress = _percent(record.get("ProgressPercentage"))
    inspected = _register_day(record.get("InspectionDate")) if progress is not None else None
    report = record.get("LatestReport")
    report_fields = {
        "inspection_company": "",
        "progress_report_valid_until": None,
        "progress_report_url": "",
    }
    if (
        isinstance(report, dict)
        and inspected is not None
        and _register_day(report.get("InspectionDate")) == inspected
        and _percent(report.get("CompletionPercentage")) == progress
    ):
        url = _text(report.get("Report"), 2000)
        report_fields = {
            "inspection_company": _text(report.get("InspectionCompany"), 120),
            "progress_report_valid_until": _register_day(report.get("ValidityDate")),
            "progress_report_url": url if urlsplit(url).scheme == "https" else "",
        }
    sold_original = _text(record.get("SoldUnit"), 40)
    sold = re.fullmatch(r"(\d{1,3}(?:\.\d{1,2})?)%", sold_original)
    sold_percent = Decimal(sold[1]) if sold and Decimal(sold[1]) <= 100 else None
    return {
        "authority": "adrec",
        "record_id": str(record["Id"]),
        "fact_scope": source.get("fact_scope", "project"),
        "registration_number": record["ProjectNumber"],
        "permit_number": _text(record.get("PermitNumber"), 40),
        "register_status": _text(record.get("Status"), 40),
        "off_plan": record.get("IsOffplan") if type(record.get("IsOffplan")) is bool else None,
        "registered_on": _register_day(record.get("ProjectCreateDate")),
        "progress_percent": progress,
        "progress_inspected_on": inspected,
        **report_fields,
        "sold_percent": sold_percent,
        "sold_original": sold_original,
        "escrow_bank_name": _text(record.get("EscrowBankName"), 160),
        "escrow_account_number": _text(record.get("EscrowNumber"), 40),
        "developer_licence": _text(record.get("DeveloperTradeLicense"), 40),
        "evidence_pointer": pointer,
    }
