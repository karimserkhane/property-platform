"""Versioned interpretation of recorded uses, never proof of current occupancy."""

import re
from typing import Literal

VERSION = "source-use-v1"
UseType = Literal[
    "school",
    "university",
    "nursery",
    "mosque",
    "worship",
    "hospital",
    "healthcare",
    "rail_station",
    "bus_station",
    "rail",
    "restaurant",
    "cafe",
    "retail",
    "office",
    "commercial",
    "mixed_use",
    "villa",
    "townhouse",
    "housing",
    "hotel",
    "park",
    "open_space",
    "beach",
    "sports",
    "parking",
    "infrastructure",
    "project_perimeter",
]


def use_types(*, land_use="", kind="", tags=None) -> list[UseType]:
    """Allowlisted tags and exact kind; no inference from a place/project name."""
    tags = tags if isinstance(tags, dict) else {}
    semantic_keys = (
        "amenity",
        "building",
        "shop",
        "leisure",
        "tourism",
        "railway",
        "public_transport",
    )
    # Captured tags take precedence over a catalogue kind read during an update.
    observed_kind = "" if any(key in tags for key in semantic_keys) else kind
    values = [land_use, observed_kind] + [
        tags.get(k, "")
        for k in (
            "amenity",
            "building",
            "shop",
            "leisure",
            "tourism",
            "railway",
            "public_transport",
        )
    ]
    text = "|".join(re.sub(r"[\s_-]+", "", v.lower()) for v in values if isinstance(v, str))
    result: list[UseType] = []
    rules = [
        ("school", ("school",)),
        ("university", ("university", "college")),
        ("nursery", ("nursery", "kindergarten")),
        ("mosque", ("mosque", "masjed", "masjid")),
        ("hospital", ("hospital",)),
        ("healthcare", ("healthcare", "clinic", "medical", "pharmacy")),
        ("bus_station", ("busstation", "busterminal")),
        ("rail", ("railway", "railland", "railroad", "railtransport", "tram")),
        ("restaurant", ("restaurant",)),
        ("cafe", ("cafe",)),
        ("retail", ("retail", "retial", "mall")),
        ("office", ("office",)),
        ("commercial", ("commercial", "commerical")),
        ("mixed_use", ("multiusage",)),
        ("villa", ("villa",)),
        ("townhouse", ("townhouse", "terrace")),
        (
            "housing",
            (
                "residen",
                "apartments",
                "multiunit",
                "multiresidential",
                "singleunit",
                "detached",
                "dormitory",
            ),
        ),
        ("hotel", ("hotel", "resort")),
        ("park", ("park/", "mixedpark", "garden")),
        ("open_space", ("openspace", "openarea", "publicrealm")),
        ("beach", ("beach",)),
        (
            "sports",
            (
                "sportclub",
                "sportfacility",
                "sportsclub",
                "sportsfield",
                "sportscentre",
                "sportscenter",
                "pitch",
                "fitness",
                "swimmingpool",
            ),
        ),
        ("parking", ("parking",)),
        (
            "infrastructure",
            (
                "substation",
                "utilities",
                "telecom",
                "cooling",
                "transformer",
                "gsm",
                "power",
                "sewage",
            ),
        ),
        ("project_perimeter", ("projectlimit",)),
    ]
    # A station may be telecom/electric: require actual railway semantics.
    if tags.get("railway") in ("station", "halt", "tram_stop") or any(
        s in text for s in ("railwaystation", "railstation", "tramstation")
    ):
        result.append("rail_station")
    if "placeofworship" in text:
        result.append("mosque" if tags.get("religion") == "muslim" else "worship")
    if any(isinstance(v, str) and v.lower().strip() == "park" for v in values):
        result.append("park")
    if any(isinstance(v, str) and v.lower().strip() in {"sport", "sports"} for v in values):
        result.append("sports")
    if any(isinstance(v, str) and v.lower().strip() == "rail" for v in values):
        result.append("rail")
    if any(isinstance(v, str) and v.lower().strip() == "house" for v in values):
        result.append("housing")
    if isinstance(tags.get("shop"), str) and tags["shop"] not in {"", "no", "vacant"}:
        result.append("retail")
    for code, terms in rules:
        if any(term in text for term in terms) and code not in result:
            result.append(code)
    if "rail_station" in result and "rail" in result:
        result.remove("rail")
    if "retail" in result and "commercial" in result:
        result.remove("commercial")
    if any(code in result for code in ("villa", "townhouse")) and "housing" in result:
        result.remove("housing")
    return result
