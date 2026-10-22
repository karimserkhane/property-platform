"""Source-backed neighbourhood amenities; proximity never establishes identity."""

from django.db import connection, transaction

from property_platform.modules.catalog.map_queries import nearby_place_rows
from property_platform.modules.evidence.queries import map_provenances, map_usage_tags

from .place_display import distinct_places
from .uses import use_types

GROUPS = {
    "education": {"school", "nursery", "university"},
    "shopping": {"retail"},
    "health": {"hospital", "healthcare"},
    "transport": {"rail_station", "bus_station", "bus_stop"},
    "leisure": {"park", "open_space", "beach", "sports"},
    "dining": {"restaurant", "cafe"},
    "worship": {"mosque", "worship"},
}


def surroundings(target, identity, *, namespaces=None, parcel_namespaces=None):
    # An existing transaction remains the caller's responsibility.
    if connection.in_atomic_block:
        return _surroundings(target, identity, namespaces, parcel_namespaces)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        return _surroundings(target, identity, namespaces, parcel_namespaces)


def _surroundings(target, identity, namespaces, parcel_namespaces):
    result = nearby_place_rows(
        target, identity, namespaces=namespaces, parcel_namespaces=parcel_namespaces
    )
    if result is None:
        return None
    rows, truncated = result
    rows = distinct_places(rows)
    sources = map_provenances("place", [row["id"] for row in rows], include_capture_id=True)
    tags = map_usage_tags(
        "place",
        [row["id"] for row in rows],
        {key: source.pop("_capture_id") for key, source in sources.items()},
    )
    groups = {key: [] for key in GROUPS}
    seen = set()
    for row in rows:
        key = str(row["id"])
        source = sources.get(key)
        if source is None or source["url"] in seen:
            continue
        types = use_types(kind=row["kind"], tags=tags.get(key))
        group = next((key for key, values in GROUPS.items() if values.intersection(types)), None)
        if group is None or len(groups[group]) >= 3:
            continue
        seen.add(source["url"])
        groups[group].append(
            {
                "id": row["id"],
                "name": row["name"],
                "name_ar": row["name_ar"],
                "use_types": types,
                "distance_m": round(row["distance"].m, 1),
                "source": source,
            }
        )
    return {
        "radius_m": 1500,
        "distance_basis": "point" if target == "place" else "centroid",
        "truncated": truncated,
        "groups": [{"key": key, "items": items} for key, items in groups.items() if items],
    }
