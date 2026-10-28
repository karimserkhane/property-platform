"""Portable extraction of reviewed project facts; no network, ORM or media downloads."""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .property_protocol import MAX_CAPTURE_BYTES, safe_url, validate_receipts

# Reviewed JSON registries stay at the evidence root (A09).
REGISTRIES = Path(__file__).parent.parent
PARSER_VERSION = "project-facts-v2"
MAX_PROJECT_RECEIPT_BYTES = 32 * 1024 * 1024
PARSERS = frozenset(
    {
        "reportage_project_v1",
        "reportage_offer_v1",
        "bloom_project_v1",
        "aldar_project_v1",
        "official_project_v1",
        "psi_project_v1",
        "adrec_project_v1",
        "propertyfinder_project_v1",
        "bayut_guide_v1",
        "terms_v1",
    }
)
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
    rows = json.loads((REGISTRIES / "project_registry.json").read_text("utf-8"))
    for row in rows:
        _validate_dated_links(row)
    scope = territory
    slug, source_key = None, None
    if territory is not None and ":" in territory:
        parts = territory.split(":")
        if len(parts) not in (2, 3):
            raise ValueError("Invalid project source scope")
        territory, slug = parts[:2]
        source_key = parts[2] if len(parts) == 3 else None
    if territory is not None and territory not in {row["territory_id"] for row in rows}:
        raise ValueError("Project territory is not registered")
    selected = tuple(
        row
        for row in rows
        if (territory is None or row["territory_id"] == territory)
        and (slug is None or row["slug"] == slug)
    )
    if not selected:
        raise ValueError(f"Project scope is not registered: {scope}")
    if source_key is not None:
        project = selected[0]
        sources = [
            row
            for row in project["sources"]
            if row["role"] != "terms"
            and hashlib.sha256(row["url"].encode()).hexdigest() == source_key
        ]
        if len(sources) != 1:
            raise ValueError("Project source scope is not registered")
        terms = sources[0].get("terms_url")
        sources += [
            row for row in project["sources"] if row["role"] == "terms" and row["url"] == terms
        ]
        selected = ({**project, "sources": sources},)
    return selected


def _validate_dated_links(project):
    """A dated identity review cites one of its project's registered pages."""
    pages = {row["url"] for row in project["sources"] if row["role"] != "terms"}
    for link in project["identity_links"]:
        dated = {"reviewed_on", "source_url"} & link.keys()
        if not dated:
            continue
        if len(dated) != 2 or link["source_url"] not in pages:
            raise ValueError("A dated identity link must cite a registered project page")
        date.fromisoformat(link["reviewed_on"])


RELATION_KINDS = frozenset({"part_of"})


def project_relations(territory=None):
    """Reviewed parent/component links between registered projects; never a merge.

    Each link cites a registered, non-terms source of either project, so its capture is
    replayed by the catalogue pipelines. A project has at most one parent and the graph
    has no cycle. A project scope such as `territory:slug` selects its territory.
    """
    rows = json.loads((REGISTRIES / "project_relations.json").read_text("utf-8"))
    # The complete reviewed file, even when a caller narrows the registry it imports.
    registry = json.loads((REGISTRIES / "project_registry.json").read_text("utf-8"))
    projects = {row["slug"]: row for row in registry}
    validate_project_relations(rows, projects)
    territory = territory.split(":")[0] if territory else None
    return tuple(
        row
        for row in rows
        if territory is None or projects[row["child"]]["territory_id"] == territory
    )


def validate_project_relations(rows, projects):
    parents = {}
    for row in rows:
        child, parent = projects.get(row.get("child")), projects.get(row.get("parent"))
        if child is None or parent is None or child is parent:
            raise ValueError("A project relation must join two registered projects")
        if child["territory_id"] != parent["territory_id"]:
            raise ValueError("A project relation stays within one territory")
        if row.get("kind") not in RELATION_KINDS:
            raise ValueError("Unknown project relation kind")
        sources = {
            source["url"]
            for project in (child, parent)
            for source in project["sources"]
            if source["role"] != "terms"
        }
        if row.get("source_url") not in sources:
            raise ValueError("A project relation must cite a registered project source")
        if not all(
            isinstance(row.get(key), str) and row[key].strip() and len(row[key]) <= limit
            for key, limit in (("component", 120), ("basis", 500), ("reviewed_on", 10))
        ):
            raise ValueError("A project relation needs its component, basis and review date")
        if row["child"] in parents:
            raise ValueError("A project has at most one parent")
        parents[row["child"]] = row["parent"]
    for start in parents:
        seen, slug = {start}, parents[start]
        while slug in parents:
            if slug in seen:
                raise ValueError("Project relations must not form a cycle")
            seen.add(slug)
            slug = parents[slug]


VERIFICATION_PAGE = re.compile(r"https://www\.dari\.ae/en/app/directory/project/[1-9][0-9]{0,9}")


def project_verification_links(territory=None):
    """Reviewed official verification pages of registered project registrations.

    An operator opens the page and records it; nothing is collected from it (B01). The
    registration number must be one a registered ADREC source of the project carries,
    so every link traces to a collected register record. `territory:slug` selects a
    territory like the other registries.
    """
    rows = json.loads((REGISTRIES / "project_verification_links.json").read_text("utf-8"))
    registry = json.loads((REGISTRIES / "project_registry.json").read_text("utf-8"))
    projects = {row["slug"]: row for row in registry}
    validate_project_verification_links(rows, projects)
    territory = territory.split(":")[0] if territory else None
    return tuple(
        row
        for row in rows
        if territory is None or projects[row["project"]]["territory_id"] == territory
    )


def validate_project_verification_links(rows, projects):
    if not isinstance(rows, list):
        raise ValueError("Expected a list of reviewed verification links")
    seen, pages = set(), {}
    for row in rows:
        project = projects.get(row.get("project"))
        if project is None:
            raise ValueError("A verification link must name a registered project")
        numbers = {
            source.get("registration_number")
            for source in project["sources"]
            if source.get("parser") == "adrec_project_v1"
        }
        number = row.get("registration_number")
        if number not in numbers:
            raise ValueError("A verification link must cite a registered ADREC registration")
        url = row.get("url")
        if not isinstance(url, str) or not VERIFICATION_PAGE.fullmatch(url):
            raise ValueError("A verification link must be an official DARI project page")
        basis = row.get("basis")
        if not isinstance(basis, str) or not basis.strip() or len(basis) > 500:
            raise ValueError("A verification link needs its basis")
        date.fromisoformat(row.get("reviewed_on") or "")
        key = (row["project"], number)
        if key in seen:
            raise ValueError("A registration has at most one verification page")
        seen.add(key)
        if pages.setdefault(url, number) != number:
            raise ValueError("A verification page belongs to one registration")


MARKET_LABEL_EVIDENCE = frozenset({"project_name", "register_name"})


def _label_key(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold()) if isinstance(value, str) else ""


def project_market_labels(territory=None):
    """Reviewed ADREC sales labels of registered projects (C01); never a fuzzy match.

    ADREC sales name a project by free text within a district, without a register
    number. A label links to a project only when it equals, ignoring case, spaces and
    punctuation, the project's registered name or the name of one of its registered
    ADREC registrations, in the same district. `territory:slug` selects a territory.
    """
    rows = json.loads((REGISTRIES / "project_market_labels.json").read_text("utf-8"))
    registry = json.loads((REGISTRIES / "project_registry.json").read_text("utf-8"))
    projects = {row["slug"]: row for row in registry}
    validate_project_market_labels(rows, projects)
    territory = territory.split(":")[0] if territory else None
    return tuple(
        row
        for row in rows
        if territory is None or projects[row["project"]]["territory_id"] == territory
    )


def validate_project_market_labels(rows, projects):
    from ..sources.adrec import DISTRICTS

    if not isinstance(rows, list):
        raise ValueError("Expected a list of reviewed market labels")
    seen = set()
    for row in rows:
        project = projects.get(row.get("project"))
        if project is None:
            raise ValueError("A market label must name a registered project")
        district = DISTRICTS.get(project["territory_id"])
        if district in (None, "all") or row.get("district") != district:
            raise ValueError("A market label belongs to the ADREC district of its project")
        label = row.get("label")
        if not isinstance(label, str) or label != label.strip() or not 1 <= len(label) <= 255:
            raise ValueError("A market label must be the exact ADREC project name")
        evidence = row.get("evidence")
        number = row.get("registration_number", "")
        if evidence == "project_name":
            names, valid = {project["name"]}, number == ""
        elif evidence == "register_name":
            sources = [
                source
                for source in project["sources"]
                if source.get("parser") == "adrec_project_v1"
                and source.get("registration_number") == number
            ]
            names, valid = {alias for s in sources for alias in s["heading_aliases"]}, bool(sources)
        else:
            raise ValueError("Unknown market label evidence")
        if not valid or _label_key(label) not in {_label_key(name) for name in names}:
            raise ValueError("A market label must equal its cited registered name")
        basis = row.get("basis")
        if not isinstance(basis, str) or not basis.strip() or len(basis) > 500:
            raise ValueError("A market label needs its basis")
        date.fromisoformat(row.get("reviewed_on") or "")
        if (district, label) in seen:
            raise ValueError("An ADREC label designates at most one project")
        seen.add((district, label))


def project_urls(projects):
    """Only HTML/terms acquisition URLs; media references are deliberately excluded."""
    if not isinstance(projects, (tuple, list)) or not 1 <= len(projects) <= 200:
        raise ValueError("Expected a bounded reviewed project registry")
    registered = {row["slug"]: row for row in project_registry()}
    for project in projects:
        full = registered.get(project.get("slug"))
        if full is None or {**project, "sources": full["sources"]} != full:
            raise ValueError("Project configuration is not an exact reviewed registry entry")
        if not project["sources"] or any(
            source not in full["sources"] for source in project["sources"]
        ):
            raise ValueError("Project source is not an exact reviewed registry entry")
        for source in project["sources"]:
            terms = source.get("terms_url")
            if any(
                row["role"] == "terms" and row["url"] == terms for row in full["sources"]
            ) and not any(
                row["role"] == "terms" and row["url"] == terms for row in project["sources"]
            ):
                raise ValueError("Required reviewed source terms are absent")
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
    hosts = {
        urlsplit(project["website_url"]).hostname,
        *(urlsplit(url).hostname for url in reviewed),
        *project.get("media_hosts", []),
    }
    result = []
    for index, node in enumerate(nodes):
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
        url = urljoin(project.get("media_base_url", project["website_url"]), url)
        parts = urlsplit(url)
        if (
            not safe_url(url)
            or parts.hostname not in hosts
            or parts.fragment
            or len(url) > 4000
            or re.search(r"(?:signature|token|expires|x-amz-|x-goog-)", parts.query, re.I)
        ):
            continue
        if any(item["source_url"] == url for item in result):
            continue
        row = reviewed.get(url)
        if row is None:
            if parts.path.lower().endswith(".pdf"):
                name = parts.path.rsplit("/", 1)[-1]
                role = (
                    "floor_plan"
                    if re.search(r"floor|layout|unit[-_ ]?types", name, re.I)
                    else "brochure"
                    if "brochure" in name.lower()
                    else "factsheet"
                )
                row = {
                    "source_url": url,
                    "kind": "document",
                    "role": role,
                    "title": f"{project['name']} · {node.text() or name}"[:255],
                    "mime_type": "application/pdf",
                }
            elif parts.hostname in {"vimeo.com", "www.youtube.com", "youtu.be"} and re.fullmatch(
                r"/(?:[0-9]+|watch|[A-Za-z0-9_-]+)", parts.path
            ):
                row = {
                    "source_url": url,
                    "kind": "video",
                    "role": "tour",
                    "title": f"{project['name']} · {node.text() or 'Video'}"[:255],
                    "mime_type": "text/html",
                }
            else:
                continue
        result.append(
            {
                **row,
                "rights_status": "reference_only",
                "original_text": original[:500],
                "evidence_pointer": f'a[href="{original}"]'
                if len(original) < 450
                else f"a:href[{index}]:sha256={hashlib.sha256(original.encode()).hexdigest()}",
            }
        )
        if len(result) > 50:
            raise ValueError("Project media link discovery exceeds its budget")
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
        labels = [
            item.text()
            for item in items
            if item.tag == "p" and item.text() in {"Total Number of Units", "Total Apartments"}
        ]
        if labels:
            if len(labels) != 1:
                raise ValueError("Project unit count label is ambiguous")
            count = next((item.text() for item in items if item.tag == "h3"), "")
            if not re.fullmatch(r"[1-9]\d{0,5}", count):
                raise ValueError("Invalid project total unit count")
            counts.append((int(count), labels[0]))
    if len(counts) != 1:
        raise ValueError("Project unit count section changed or is ambiguous")
    result.update(
        total_units=counts[0][0],
        total_units_original=f"{counts[0][0]} {counts[0][1]}",
        total_units_pointer=f".counter-card-inner:{counts[0][1]} > h3",
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
    if source["parser"] == "aldar_project_v1":
        from .project_adapters import aldar_project

        return aldar_project(project, source, receipt, _base)
    if source["parser"] == "psi_project_v1":
        from .project_psi import psi_project

        return psi_project(project, source, receipt, _base, _amenity)
    if source["parser"] == "adrec_project_v1":
        from .project_adrec import adrec_project

        return adrec_project(project, source, receipt, _base)
    if source["parser"] == "propertyfinder_project_v1":
        from .project_propertyfinder import propertyfinder_project

        return propertyfinder_project(project, source, receipt, _base)
    document = _Document(payload)
    nodes = tuple(document.root.walk())
    if not any(node.tag == "html" for node in nodes):
        raise ValueError("Project source must be an HTML document")
    if source["parser"] == "terms_v1":
        if not re.search(r"(?:Terms|Use of)", document.root.text(), re.I):
            raise ValueError("Source terms page is absent")
        return None
    if source["parser"] == "official_project_v1":
        from .project_adapters import official_project
        from .project_maryah import enrich_maryah

        return enrich_maryah(
            project,
            source,
            receipt["payload"],
            official_project(project, source, nodes, _base, _media, _amenity),
        )
    if source["parser"] == "bayut_guide_v1":
        from .project_adapters import bayut_project

        return bayut_project(project, source, nodes, _base, _media, _amenity)
    if urlsplit(source["url"]).hostname == "bloomholding.com":
        return _bloom(project, source, nodes)
    return _reportage(project, source, document.root, nodes)
