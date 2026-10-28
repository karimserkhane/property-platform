from django.db import connection, transaction

from property_platform.modules.catalog.map_queries import map_rows
from property_platform.modules.evidence.history.catalogue_history import recover_display
from property_platform.modules.evidence.projects.queries import (
    map_provenances,
    map_usage_tags,
    property_presentations,
)

from .place_display import distinct_places
from .uses import use_types

# Families a context index lists without geometry; maps draw them from context tiles.
TILED = ("street", "building")


def map_context(bbox, *, namespaces=None, parcel_namespaces=None, tiled=False):
    # Own a consistent read snapshot in an HTTP read; an existing transaction
    # remains the caller's responsibility and is never reconfigured here.
    if connection.in_atomic_block:
        return _map_context(
            bbox, namespaces=namespaces, parcel_namespaces=parcel_namespaces, tiled=tiled
        )
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        return _map_context(
            bbox, namespaces=namespaces, parcel_namespaces=parcel_namespaces, tiled=tiled
        )


def _map_context(bbox, *, namespaces=None, parcel_namespaces=None, tiled=False):
    result = {}
    for target in ("street", "building", "place", "administrative_area"):
        geometry = not (tiled and target in TILED)
        rows, truncated = map_rows(
            target,
            bbox,
            namespaces=namespaces,
            parcel_namespaces=parcel_namespaces,
            geometry=geometry,
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
            row.pop("source_namespace")
            feature = {"type": "Feature", "id": identity}
            if geometry:
                feature["geometry"] = row.pop("geometry")
            result[target]["features"].append(
                {
                    **feature,
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
