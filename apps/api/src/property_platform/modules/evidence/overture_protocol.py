"""Pure reviewed Overture release, scope and category protocol; no ORM or network."""

import json

from .collection_profiles import collection_for
from .onwani import SourceError

VERSION = "overture-places-v1"
RELEASE = "2026-09-23.1"
URL = f"https://overturemaps-us-west-2.s3.amazonaws.com/release/{RELEASE}/theme=places/type=place/"
MAX_ROWS = 10000
MAX_BYTES = 16 * 1024 * 1024
MIN_CONFIDENCE = 0.8


def namespace(territory):
    return collection_for(territory).map_namespace("overture")


def decode(payload, territory):
    if not isinstance(payload, bytes) or len(payload) > MAX_BYTES:
        raise SourceError("Overture extract exceeds its byte budget")
    value = json.loads(payload)
    if (
        not isinstance(value, dict)
        or value.get("release") != RELEASE
        or value.get("territory") != territory
        or value.get("bounds") != list(collection_for(territory).osm_bounds)
        or not isinstance(value.get("rows"), list)
        or not 1 <= len(value["rows"]) <= MAX_ROWS
    ):
        raise SourceError("Incomplete or unexpected Overture extract")
    return value["rows"]


def place_kind(row):
    """Interpret recorded taxonomy only; never infer a business type from its name."""
    taxonomy = row.get("taxonomy") or {}
    labels = [*(taxonomy.get("hierarchy") or []), taxonomy.get("primary", "")]
    labels = {v for v in labels if isinstance(v, str)}
    for kind, matches in (
        ("school", {"school", "primary_school", "secondary_school"}),
        ("nursery", {"preschool", "childcare", "kindergarten"}),
        ("university", {"university", "college"}),
        ("mosque", {"mosque"}),
        ("hospital", {"hospital"}),
        ("healthcare", {"health_care", "healthcare", "clinic", "pharmacy"}),
        ("cafe", {"cafe", "coffee_shop"}),
        ("restaurant", {"restaurant", "casual_eatery", "fast_food_restaurant"}),
        ("retail", {"shopping", "retail", "supermarket", "shopping_mall"}),
        ("hotel", {"hotel", "resort"}),
        ("park", {"park", "garden"}),
        ("beach", {"beach"}),
        ("sports", {"sports_and_recreation", "fitness_center", "gym"}),
        ("bus_station", {"bus_station"}),
        ("rail_station", {"train_station", "railway_station"}),
    ):
        if labels & matches:
            return kind
    primary = taxonomy.get("primary", "")
    return primary if isinstance(primary, str) and len(primary) <= 100 else ""
