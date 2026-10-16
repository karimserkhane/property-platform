"""Publisher-specific project facts from inert receipts; never infer unit availability."""

import json
import re
from datetime import date


def aldar_project(project, source, receipt, base):
    payload = json.loads(receipt["payload"])
    data = payload.get("data")
    if not isinstance(data, dict) or data.get("communityId") != project["record_id"]:
        raise ValueError("Aldar project identity changed")
    if data.get("projectName") != project["name"]:
        raise ValueError("Aldar project name changed; identity review is required")
    location = data.get("communityLocation")
    expected = "Saadiyat Island" if project["territory_id"] == "saadiyat-island" else "Reem Island"
    if not isinstance(location, str) or expected.casefold() not in location.casefold():
        raise ValueError("Aldar project location changed")
    result = base(project, source)
    count = data.get("totalUnits")
    if count is not None:
        if type(count) is not int or not 0 <= count <= 100000:
            raise ValueError("Aldar programme count changed shape")
        if count:
            result.update(
                total_units=count,
                total_units_original=str(count),
                total_units_pointer="JSON:data.totalUnits",
            )
    completion = data.get("completionDate")
    if completion:
        value = date.fromisoformat(completion)
        result["handover"] = {
            "precision": "day",
            "year": value.year,
            "month": value.month,
            "day": value.day,
            "quarter": None,
            "original_text": completion,
            "evidence_pointer": "JSON:data.completionDate (publisher-announced date)",
        }
    kinds = {
        "Apartment": "apartment",
        "Penthouse": "penthouse",
        "Villa": "villa",
        "TownHouse": "townhouse",
        "Duplex": "duplex",
    }
    types = data.get("unitTypes")
    bedrooms = data.get("bedrooms")
    if not isinstance(types, list) or not isinstance(bedrooms, list):
        raise ValueError("Aldar residential types changed shape")
    residential = list(dict.fromkeys(kinds[item] for item in types if item in kinds))
    if len(residential) == 1:
        for item in dict.fromkeys(bedrooms):
            if item == "Studio":
                value = 0
            elif isinstance(item, str) and re.fullmatch(r"[1-9]|1[0-9]|20", item):
                value = int(item)
            else:
                continue
            result["typologies"].append(
                {
                    "property_type": residential[0],
                    "bedrooms": value,
                    "original_text": f"{types!r}; bedrooms={item}",
                    "evidence_pointer": "JSON:data.unitTypes + data.bedrooms (single type)",
                }
            )
    else:
        # Arrays are not a list of pairs: never cross-join bedroom counts and home types.
        result["typologies"] = [
            {
                "property_type": kind,
                "bedrooms": None,
                "original_text": str(types),
                "evidence_pointer": "JSON:data.unitTypes; bedroom association unspecified",
            }
            for kind in residential
        ]
    return result


def _content_nodes(nodes):
    root = next((node for node in nodes if node.tag == "main"), None)
    root = root or next((node for node in nodes if node.tag == "body"), nodes[0])

    def walk(node):
        if node.tag in {"header", "footer", "nav", "form", "script", "style"}:
            return
        if re.search(
            r"(?:^|[ _-])(?:related|footer|navigation)(?:$|[ _-])",
            node.attrs.get("class", ""),
            re.I,
        ):
            return
        yield node
        for child in node.children:
            if not isinstance(child, str):
                yield from walk(child)

    return tuple(walk(root))


def _publisher_facts(project, nodes, result):
    publisher = project["developer"]["key"]
    counts = []
    for index, node in enumerate(nodes):
        text = node.text()
        match = None
        if publisher == "saas-properties" and node.has_class("flex-col"):
            match = re.fullmatch(r"Units\s+([1-9]\d{0,5})", text)
        elif publisher == "radiant-real-estate" and node.has_class(
            "bt_bb_real_estate_details_content"
        ):
            match = re.fullmatch(r"RESIDENTIAL UNITS\s+([1-9]\d{0,5})", text)
        elif publisher == "reportage-properties" and node.has_class("counter-card-inner"):
            match = re.fullmatch(r"([1-9]\d{0,5})\s+Total Number of Units", text)
        elif publisher == "bloom-holding" and node.has_class("fade-up-text"):
            match = re.fullmatch(r"([1-9]\d{0,5})\s+units", text, re.I)
        if match:
            counts.append((int(match[1]), text, f"{node.tag}:programme-label[{index}]"))
    if len({row[0] for row in counts}) > 1:
        raise ValueError("Conflicting programme totals on the project page")
    if counts:
        result.update(
            zip(
                ("total_units", "total_units_original", "total_units_pointer"),
                counts[0],
                strict=True,
            )
        )

    kinds = {
        "apartment": "apartment",
        "duplex": "duplex",
        "penthouse": "penthouse",
        "townhouse": "townhouse",
        "villa": "villa",
    }
    typologies = []
    for index, node in enumerate(nodes):
        if publisher == "bloom-holding" and node.has_class("unit"):
            card = tuple(node.walk())
            kind = next(
                (kinds.get(item.text().lower().rstrip("s")) for item in card if item.tag == "h3"),
                None,
            )
            if kind is None:
                continue
            for item in card:
                if item.tag != "span":
                    continue
                match = re.match(r"^(Studio|([0-9]{1,2}) Bedrooms?),", item.text(), re.I)
                if match:
                    typologies.append(
                        (
                            kind,
                            int(match[2]) if match[2] else 0,
                            item.text(),
                            f".unit[{index}]:h3 + span",
                        )
                    )
        if node.tag in {"h3", "h4", "button"}:
            match = re.fullmatch(
                r"([0-9]{1,2})[ -]+Bedrooms?\s+(Apartment|Duplex|Penthouse|Townhouse|Villa)s?",
                node.text(),
                re.I,
            )
            if match:
                typologies.append(
                    (
                        kinds[match[2].lower()],
                        int(match[1]),
                        node.text(),
                        f"{node.tag}:layout[{index}]",
                    )
                )
    if publisher == "saas-properties":
        types = [
            node.text()
            for node in nodes
            if node.has_class("flex-col") and node.text().startswith("Property Type ")
        ]
        rooms = [
            node.text()
            for node in nodes
            if node.has_class("flex-col") and node.text().startswith("Bedrooms ")
        ]
        if set(types) == {"Property Type Apartments"} and len(set(rooms)) == 1:
            text = rooms[0].removeprefix("Bedrooms ")
            if re.fullmatch(r"(?:Studio|[0-9]{1,2})(?:,\s*(?:Studio|[0-9]{1,2}))*", text, re.I):
                for room in text.split(","):
                    typologies.append(
                        (
                            "apartment",
                            0 if room.strip().lower() == "studio" else int(room),
                            rooms[0],
                            "project statistics:Property Type + Bedrooms",
                        )
                    )
    seen = set()
    for kind, bedrooms, original, pointer in typologies:
        if bedrooms > 20 or (kind, bedrooms) in seen:
            continue
        seen.add((kind, bedrooms))
        result["typologies"].append(
            {
                "property_type": kind,
                "bedrooms": bedrooms,
                "original_text": original[:500],
                "evidence_pointer": pointer,
            }
        )


def official_project(project, source, nodes, base, media, amenity):
    def normalize(value):
        return re.sub(r"[^a-z0-9]+", "", value.casefold())

    expected = [
        normalize(value) for value in [project["name"], *project.get("heading_aliases", [])]
    ]
    identities = [node.text() for node in nodes if node.tag in {"h1", "title"}]
    identities += [
        node.attrs.get("content", "")
        for node in nodes
        if node.tag == "meta" and node.attrs.get("property") == "og:title"
    ]
    if not any(name and name in normalize(value) for value in identities for name in expected):
        raise ValueError("Official project heading no longer matches its reviewed identity")
    result = base(project, source)
    descriptions = [
        node.attrs.get("content", "")
        for node in nodes
        if node.tag == "meta" and node.attrs.get("name", "").lower() == "description"
    ]
    if descriptions and any(name in normalize(descriptions[0]) for name in expected):
        result["summary"] = descriptions[0].strip()[:450]
    nodes = _content_nodes(nodes)
    _publisher_facts(project, nodes, result)
    result["media"] = media(project, nodes)
    # Only individually labelled amenity items are accepted, never footer/site-wide copy.
    for index, node in enumerate(nodes):
        if node.tag == "li" and node.has_class("amenity-item"):
            row = amenity(node.text(), f"li.amenity-item[{index}]")
            if row and not any(item["code"] == row["code"] for item in result["amenities"]):
                result["amenities"].append(row)
    return result
