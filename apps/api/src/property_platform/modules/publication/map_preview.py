from django.db import connection, transaction

from property_platform.modules.catalog.map_queries import map_rows
from property_platform.modules.evidence.catalogue_history import recover_display
from property_platform.modules.evidence.queries import (
    map_provenances,
    map_usage_tags,
    property_presentations,
)

from .place_display import distinct_places
from .uses import use_types


def map_context(bbox, *, namespaces=None, parcel_namespaces=None):
    # Own a consistent read snapshot in an HTTP read; an existing transaction
    # remains the caller's responsibility and is never reconfigured here.
    if connection.in_atomic_block:
        return _map_context(bbox, namespaces=namespaces, parcel_namespaces=parcel_namespaces)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        return _map_context(bbox, namespaces=namespaces, parcel_namespaces=parcel_namespaces)


def _map_context(bbox, *, namespaces=None, parcel_namespaces=None):
    result = {}
    for target in ("street", "building", "place", "administrative_area"):
        rows, truncated = map_rows(
            target, bbox, namespaces=namespaces, parcel_namespaces=parcel_namespaces
        )
        if target == "place":
            rows = distinct_places(rows)
        recover_display(target, rows)
        sources = map_provenances(target, [row["id"] for row in rows], include_capture_id=True)
        tags = map_usage_tags(
            target,
            [row["id"] for row in rows],
            {identity: source.pop("_capture_id") for identity, source in sources.items()},
        )
        presentations = property_presentations(target, [row["id"] for row in rows])
        result[target] = {"type": "FeatureCollection", "truncated": truncated, "features": []}
        for row in rows:
            identity = str(row.pop("id"))
            source = sources.get(identity)
            if source is None:
                continue
            geometry = row.pop("geometry")
            row.pop("source_namespace")
            result[target]["features"].append(
                {
                    "type": "Feature",
                    "id": identity,
                    "geometry": geometry,
                    "properties": {
                        "id": identity,
                        **row,
                        "use_types": use_types(kind=row["kind"], tags=tags.get(identity)),
                        "source": source,
                        "presentation": presentations.get(identity),
                    },
                }
            )
    return result
