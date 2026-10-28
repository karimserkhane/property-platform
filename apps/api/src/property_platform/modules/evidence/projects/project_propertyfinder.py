"""Reviewed public project pages; listing inventory and investment claims stay out."""

import json
import math
import re
from datetime import datetime
from urllib.parse import urlsplit


def _name(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold()) if isinstance(value, str) else ""


def propertyfinder_candidates(definition, payload):
    from .project_protocol import _Document

    nodes = [
        n
        for n in _Document(payload).root.walk()
        if n.tag == "script" and n.attrs.get("id") == "__NEXT_DATA__"
    ]
    if len(nodes) != 1:
        raise ValueError("Property Finder catalogue data are absent or ambiguous")
    data = json.loads("".join(c for c in nodes[0].children if isinstance(c, str)))
    result = data.get("props", {}).get("pageProps", {}).get("searchResult", {})
    body, metadata = result.get("data", {}), result.get("meta", {})
    total = metadata.get("count", {}).get("total")
    pagination, records = metadata.get("pagination", {}), body.get("projects")
    expected_island = {
        "al-reem-island": "Al Reem Island",
        "saadiyat-island": "Saadiyat Island",
        "al-maryah-island": "Al Maryah Island",
    }[definition["territory_scope"]]
    page = definition["page"]
    if (
        type(total) is not int
        or not 1 <= total <= 48
        or pagination != {"page": page, "total": math.ceil(total / 24)}
        or not isinstance(records, list)
        or len(records) != min(24, total - (page - 1) * 24)
        or body.get("locationTitle") != expected_island
    ):
        raise ValueError("Property Finder catalogue pagination or island changed")
    rows, seen = [], set()
    for i, record in enumerate(records):
        identifier, title, link = record.get("id"), record.get("title"), record.get("shareUrl")
        if (
            not isinstance(identifier, str)
            or not re.fullmatch(r"[a-f0-9-]{36}", identifier)
            or identifier in seen
            or not isinstance(title, str)
            or not title.strip()
            or not isinstance(link, str)
            or not re.fullmatch(r"/en/new-projects/[a-z0-9-]+/[a-z0-9-]+", link)
        ):
            raise ValueError("Property Finder catalogue identity changed")
        seen.add(identifier)
        rows.append(
            {
                "source_url": "https://www.propertyfinder.ae" + link,
                "source_record_id": identifier,
                "title": title[:255],
                "original_text": title[:500],
                "evidence_pointer": (
                    f"JSON:props.pageProps.searchResult.data.projects[{i}].id/title/shareUrl"
                ),
            }
        )
    return rows


def propertyfinder_record(project, source, payload):
    from .project_protocol import _Document

    if type(payload) is not bytes or not 0 < len(payload) <= 4 * 1024 * 1024:
        raise ValueError("Property Finder project exceeds its response budget")
    scripts = [
        node
        for node in _Document(payload).root.walk()
        if node.tag == "script" and node.attrs.get("id") == "__NEXT_DATA__"
    ]
    if len(scripts) != 1:
        raise ValueError("Property Finder project data are absent or ambiguous")
    data = json.loads("".join(c for c in scripts[0].children if isinstance(c, str)))
    row = data.get("props", {}).get("pageProps", {}).get("detailResult")
    parts = urlsplit(source["url"])
    island = {"al-reem-island": 279, "saadiyat-island": 310}.get(project["territory_id"])
    if island is None:
        raise ValueError("Property Finder project territory has no reviewed source identity")
    if (
        not isinstance(row, dict)
        or parts.hostname != "www.propertyfinder.ae"
        or parts.query
        or parts.fragment
        or parts.path != "/en/new-projects/" + str(row.get("slug"))
        or row.get("id") != source["record_id"]
        or _name(row.get("title")) not in {_name(v) for v in source["heading_aliases"]}
        or _name(row.get("developer", {}).get("name"))
        not in {_name(v) for v in source["developer_aliases"]}
        or not any(
            r.get("id") == 6 and r.get("type") == "CITY" for r in row.get("locationTree", [])
        )
        or not any(
            r.get("id") == island and r.get("type") == "COMMUNITY"
            for r in row.get("locationTree", [])
        )
    ):
        raise ValueError("Property Finder project identity, party or territory changed")
    return row


def propertyfinder_project(project, source, receipt, base):
    from .project_protocol import _Document

    row = propertyfinder_record(project, source, receipt["payload"])
    result = base(project, source)
    result.update(
        parser_version="propertyfinder-project-v1",
        title=row["title"],
        source_developer_name=row["developer"]["name"],
        source_developer_role="declared",
    )
    description = row.get("metaDescription")
    if isinstance(description, str):
        result["summary"] = _Document(description.encode()).root.text()[:450]
    value = row.get("deliveryDate")
    if value:
        parsed = datetime.fromisoformat(value)
        if not 1900 <= parsed.year <= 2200:
            raise ValueError("Property Finder delivery date changed")
        # The page renders only a month. Day=1 and the time are CMS placeholders.
        result["handover"] = {
            "precision": "month",
            "year": parsed.year,
            "month": parsed.month,
            "quarter": None,
            "day": None,
            "original_text": value,
            "evidence_pointer": "JSON:props.pageProps.detailResult.deliveryDate (displayed month)",
        }
    kinds = {"apartment", "villa", "townhouse", "penthouse", "duplex"}
    units = row.get("units") or []
    if not isinstance(units, list) or len(units) > 100:
        raise ValueError("Property Finder unit-type structure changed")
    seen = set()
    for i, building in enumerate(units):
        for j, group in enumerate(building.get("units", [])):
            kind = group.get("propertyType")
            if kind not in kinds:
                continue
            entries = group.get("list", [])
            if not isinstance(entries, list) or len(entries) > 200:
                raise ValueError("Property Finder type breakdown exceeds its budget")
            for k, entry in enumerate(entries):
                bedrooms = entry.get("bedrooms")
                if type(bedrooms) is not int or not 0 <= bedrooms <= 20 or (kind, bedrooms) in seen:
                    continue
                seen.add((kind, bedrooms))
                result["typologies"].append(
                    {
                        "property_type": kind,
                        "bedrooms": bedrooms,
                        "original_text": f"{kind}: bedrooms={bedrooms}",
                        "evidence_pointer": (
                            f"JSON:detailResult.units[{i}].units[{j}].list[{k}].bedrooms"
                        ),
                    }
                )
    # units[].totalUnits, stockAvailability, startingPrice and salesPhase are
    # commercial listings, never the programme total or current availability.
    return result


def propertyfinder_position(project, source, payload):
    row = propertyfinder_record(project, source, payload)
    location = row.get("location") or {}
    if location.get("type") != "TOWER" or _name(location.get("name")) not in {
        _name(v) for v in source["heading_aliases"]
    }:
        return None
    coordinates = location.get("coordinates") or {}
    lat, lon = coordinates.get("lat"), coordinates.get("lon")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (lat, lon)):
        return None
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return None
    for a, b in [(24.4942437, 54.4068603), (24.5302924, 54.4451578)]:
        if math.hypot((lat - a) * 111320, (lon - b) * 111320 * math.cos(math.radians(lat))) < 30:
            return None
    return {
        "lat": lat,
        "lon": lon,
        "source_kind": "broker",
        "publisher_key": "propertyfinder",
        "source_name": "Property Finder",
        "method": "broker_project_coordinates",
        "evidence_pointer": "JSON:props.pageProps.detailResult.location.coordinates (named tower)",
    }
