"""Portable extraction of reviewed project facts; no network, ORM or media downloads."""

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from .property_protocol import MAX_CAPTURE_BYTES, safe_url, validate_receipts

PARSER_VERSION = "project-facts-v1"
MAX_PROJECT_RECEIPT_BYTES = 32 * 1024 * 1024
PARSERS = frozenset({"reportage_project_v1", "reportage_offer_v1", "bloom_project_v1", "terms_v1"})
_VOID = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


def project_registry(territory=None):
    """Load a fresh copy of the closed, reviewed configuration, never a caller URL."""
    rows = json.loads(Path(__file__).with_name("project_registry.json").read_text("utf-8"))
    if territory is not None and territory not in {row["territory_id"] for row in rows}:
        raise ValueError("Project territory is not registered")
    return tuple(row for row in rows if territory is None or row["territory_id"] == territory)


def project_urls(projects):
    """Only HTML/terms acquisition URLs; media references are deliberately excluded."""
    if not isinstance(projects, (tuple, list)) or not 1 <= len(projects) <= 200:
        raise ValueError("Expected a bounded reviewed project registry")
    registered = {row["slug"]: row for row in project_registry()}
    for project in projects:
        if registered.get(project.get("slug")) != project:
            raise ValueError("Project configuration is not an exact reviewed registry entry")
    urls = tuple(dict.fromkeys(source["url"] for row in projects for source in row["sources"]))
    if len(urls) > 400 or any(not safe_url(url) for url in urls):
        raise ValueError("Invalid reviewed project source URLs")
    return urls


def validate_project_receipts(rows, projects):
    return validate_receipts(rows, set(project_urls(projects)))


@dataclass
class _Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, _Node):
                yield from child.walk()

    def text(self):
        if self.tag in {"script", "style", "noscript", "template"}:
            return ""
        return _clean(
            " ".join(child.text() if isinstance(child, _Node) else child for child in self.children)
        )

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()


class _Document(HTMLParser):
    def __init__(self, payload):
        super().__init__(convert_charrefs=True)
        self.root = _Node("document")
        self.stack = [self.root]
        self.feed(payload.decode("utf-8", errors="strict"))
        self.close()

    def handle_starttag(self, tag, attrs):
        if len(self.stack) > 200:
            raise ValueError("Project HTML nesting exceeds the parser budget")
        node = _Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Node(tag, dict(attrs)))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _clean(value):
    return re.sub(r"\s+", " ", value).strip()


def _base(project, source):
    return {
        "project_slug": project["slug"],
        "source_url": source["url"],
        "source_role": source["role"],
        "parser_version": PARSER_VERSION,
        "title": project["name"],
        "summary": "",
        "handover": None,
        "total_units": None,
        "typologies": [],
        "amenities": [],
        "media": [],
        "rights_status": source["rights_status"],
        "terms_url": source["terms_url"],
        "acquisition_scope": source["acquisition_scope"],
    }


_AMENITIES = {
    "large swimming pools": "swimming_pool",
    "swimming pool": "swimming_pool",
    "kids’ swimming pools": "children_pool",
    "kids' swimming pools": "children_pool",
    "kids’ area": "children_play_area",
    "kids' play area": "children_play_area",
    "kids play area": "children_play_area",
    "gym & fitness centre": "gym",
    "gymnasium": "gym",
    "seating areas": "seating_area",
    "retail area": "retail",
    "retail": "retail",
    "landscape gardens": "landscaped_gardens",
    "lush landscaped gardens": "landscaped_gardens",
    "bbq areas": "barbecue_area",
    "parking space": "parking",
    "restaurants": "restaurants",
    "round the clock security services": "security",
}


def _amenity(value, pointer):
    code = _AMENITIES.get(value.casefold())
    return (
        None
        if code is None
        else {
            "code": code,
            "label": value,
            "original_text": value,
            "evidence_pointer": pointer,
        }
    )


def _media(project, nodes):
    reviewed = {row["source_url"]: row for row in project["media_references"]}
    result = []
    for node in nodes:
        if node.tag != "a":
            continue
        original = node.attrs.get("href", "")
        # Historical Reportage HTTP links are references only. No request follows
        # this normalization, and only an exact reviewed HTTPS target is accepted.
        url = (
            "https://" + original[7:]
            if original.startswith("http://reportageuae.com/")
            else original
        )
        if url not in reviewed or any(item["source_url"] == url for item in result):
            continue
        row = reviewed[url]
        result.append(
            {
                **row,
                "rights_status": "reference_only",
                "original_text": original,
                "evidence_pointer": f'a[href="{original}"]',
            }
        )
    return result


def _typologies(nodes, *, bloom=False):
    result = []
    for index, node in enumerate(nodes):
        # No navigation/category names or structured offers are promoted to inventory.
        if node.tag not in ({"span"} if bloom else {"button"}):
            continue
        text = node.text()
        pattern = (
            r"(Studio|[1-8] Bedrooms?), [1-9] Bathrooms?"
            if bloom
            else r"([1-8]) (?:Bedrooms?|BDR)(?: (Simplex|Duplex|Triplex|Penthouse))?"
        )
        match = re.fullmatch(pattern, text, re.I)
        if not match:
            continue
        if bloom:
            bedrooms = 0 if match[1].casefold() == "studio" else int(match[1][0])
            kind = "apartment"
        else:
            bedrooms = int(match[1])
            suffix = (match[2] or "").casefold()
            kind = (
                "penthouse"
                if suffix == "penthouse"
                else "duplex"
                if suffix == "duplex"
                else "apartment"
            )
            # Triplex is not an alias for duplex or a proven apartment typology.
            if suffix == "triplex":
                continue
        row = {
            "property_type": kind,
            "bedrooms": bedrooms,
            "original_text": text,
            "evidence_pointer": f"{node.tag}:visible-text[{index + 1}]",
        }
        if not any(
            (item["property_type"], item["bedrooms"]) == (kind, bedrooms) for item in result
        ):
            result.append(row)
    return result


def _reportage(project, source, root, nodes):
    result = _base(project, source)
    if source["parser"] == "reportage_offer_v1":
        title = next((node.text() for node in nodes if node.tag == "title"), "")
        if project["name"].casefold() not in title.casefold():
            raise ValueError("Project offer identity is absent from its HTML title")
        matches = re.findall(
            r"Q([1-4]),?\s+(20\d{2})\s+(?:Handover|Scheduled handover date)", root.text(), re.I
        )
        unique = set(matches)
        if len(unique) != 1:
            raise ValueError("Expected one unambiguous announced handover quarter")
        quarter, year = next(iter(unique))
        result["handover"] = {
            "precision": "quarter",
            "year": int(year),
            "quarter": int(quarter),
            "month": None,
            "day": None,
            "original_text": f"Q{quarter}, {year} Handover",
            "evidence_pointer": "visible-text:announced-handover",
        }
        result["typologies"] = _typologies(nodes)
        return result
    if not any(node.tag in {"h1", "h2", "h3"} and node.text() == project["name"] for node in nodes):
        raise ValueError("Project identity is absent from the expected heading")
    counters = [node for node in nodes if node.has_class("counter-card-inner")]
    counts = []
    for node in counters:
        items = tuple(node.walk())
        if any(item.tag == "p" and item.text() == "Total Number of Units" for item in items):
            count = next((item.text() for item in items if item.tag == "h3"), "")
            if not re.fullmatch(r"[1-9]\d{0,5}", count):
                raise ValueError("Invalid project total unit count")
            counts.append(int(count))
    if len(counts) != 1:
        raise ValueError("Project unit count section changed or is ambiguous")
    result.update(
        total_units=counts[0],
        total_units_original=str(counts[0]),
        total_units_pointer=".counter-card-inner:Total Number of Units > h3",
    )
    for index, node in enumerate(nodes):
        if node.tag == "li" and node.has_class("amenity-item"):
            if row := _amenity(node.text(), f"li.amenity-item[{index + 1}]"):
                result["amenities"].append(row)
    if not result["amenities"]:
        raise ValueError("Project amenities section changed or is empty")
    result["typologies"] = _typologies(nodes)
    result["media"] = _media(project, nodes)
    return result


def _bloom(project, source, nodes):
    places = []
    for node in nodes:
        if node.tag != "script" or node.attrs.get("type") != "application/ld+json":
            continue
        raw = "".join(child for child in node.children if isinstance(child, str))
        try:
            item = json.loads(raw)
        except ValueError as exc:
            raise ValueError("Project structured data is invalid") from exc
        if isinstance(item, dict) and item.get("@type") == "Place":
            places.append(item)
    if (
        len(places) != 1
        or places[0].get("name") != project["name"]
        or places[0].get("url") != source["url"]
    ):
        raise ValueError("Project structured identity is absent or ambiguous")
    place = places[0]
    description = place.get("description", "")
    count = re.search(r"\b([1-9]\d{0,5})\s+(?:spacious\s+)?residential units\b", description, re.I)
    if count is None:
        raise ValueError("Project residential count section changed")
    result = _base(project, source)
    result.update(
        total_units=int(count[1]),
        total_units_original=count[0],
        total_units_pointer="JSON-LD Place.description:residential units",
    )
    for index, item in enumerate(place.get("amenityFeature", [])):
        if isinstance(item, dict) and item.get("@type") == "LocationFeatureSpecification":
            if row := _amenity(item.get("name", ""), f"JSON-LD Place.amenityFeature[{index}].name"):
                result["amenities"].append(row)
    result["typologies"] = _typologies(nodes, bloom=True)
    if not result["amenities"] or not result["typologies"]:
        raise ValueError("Project amenities or residential types changed")
    result["media"] = _media(project, nodes)
    # JSON-LD claims InStock while visible cards say Sold Out. Neither prices nor
    # availability are extracted: these require an explicit commercial model/review.
    return result


def extract_project_source(project, source, receipt):
    """Extract bounded factual observations from a validated exact HTML receipt.

    This function grants no publication licence. Source terms and external media
    references remain restricted to local research until separately reviewed.
    """
    if source not in project["sources"] or source["parser"] not in PARSERS:
        raise ValueError("Project parser/source is not registered")
    payload = receipt.get("payload")
    if (
        receipt.get("url") != source["url"]
        or not isinstance(payload, bytes)
        or not 0 < len(payload) <= MAX_CAPTURE_BYTES
    ):
        raise ValueError("Unexpected validated project receipt")
    document = _Document(payload)
    nodes = tuple(document.root.walk())
    if not any(node.tag == "html" for node in nodes):
        raise ValueError("Project source must be an HTML document")
    if source["parser"] == "terms_v1":
        if not re.search(r"(?:Terms|Use of)", document.root.text(), re.I):
            raise ValueError("Source terms page is absent")
        return None
    if urlsplit(source["url"]).hostname == "bloomholding.com":
        return _bloom(project, source, nodes)
    return _reportage(project, source, document.root, nodes)
