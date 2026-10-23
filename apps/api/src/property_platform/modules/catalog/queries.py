"""Bounded catalogue reads; delivery code never serializes a model directly."""

import json

from django.contrib.gis.db.models import MultiPolygonField
from django.contrib.gis.db.models.functions import Area, AsGeoJSON, Envelope, PointOnSurface
from django.contrib.gis.geos import Polygon
from django.db import connection, transaction
from django.db.models.functions import Cast

from .models import Parcel


def parcel_counts(namespaces):
    from django.db.models import Count

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout='2000ms'")
        return dict(
            Parcel.objects.filter(source_namespace__in=namespaces, superseded_by__isnull=True)
            .values("source_namespace")
            .annotate(count=Count("id"))
            .values_list("source_namespace", "count")
        )


def _current_parcels(namespace=None, namespaces=None):
    records = Parcel.objects.filter(superseded_by__isnull=True)
    if namespace is not None:
        records = records.filter(source_namespace=namespace)
    if namespaces is not None:
        records = records.filter(source_namespace__in=namespaces)
    return records


def parcel_features(
    *, bbox, limit, query="", namespace=None, namespaces=None, after=None, geometry=True
):
    """Current parcels in a bbox. Without geometry, each row carries its bounds, label
    point and area instead, for clients that draw footprints from `parcel_tile`."""
    envelope = Polygon.from_bbox(bbox)
    envelope.srid = 4326
    records = _current_parcels(namespace, namespaces).filter(geometry__intersects=envelope)
    if after is not None:
        records = records.filter(id__gt=after)
    if query:
        records = records.filter(code__istartswith=query)
    fields = ["id", "code", "community", "land_use", "construction_status"]
    if geometry:
        records = records.annotate(shape=AsGeoJSON("geometry", precision=6))
        fields.append("shape")
    else:
        records = records.annotate(
            box=AsGeoJSON(Envelope("geometry"), precision=6),
            label=AsGeoJSON(PointOnSurface("geometry"), precision=6),
            area=Area(Cast("geometry", MultiPolygonField(srid=4326, geography=True))),
        )
        fields += ["box", "label", "area"]
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '2000ms'")
        rows = list(records.order_by("id").values(*fields)[: limit + 1])
    features = []
    for row in rows[:limit]:
        feature = {
            "type": "Feature",
            "id": str(row["id"]),
            "properties": {
                "id": str(row["id"]),
                "code": row["code"],
                "community": row["community"],
                "land_use": row["land_use"],
                "construction_status": row["construction_status"],
            },
        }
        if geometry:
            feature["geometry"] = json.loads(row["shape"])
        else:
            feature["properties"].update(
                bounds=_bounds(json.loads(row["box"])),
                label_point=tuple(json.loads(row["label"])["coordinates"]),
                area_m2=round(row["area"].sq_m, 1),
            )
        features.append(feature)
    return {
        "type": "FeatureCollection",
        "features": features,
        "truncated": len(rows) > limit,
        "next_cursor": str(rows[limit - 1]["id"]) if len(rows) > limit else None,
    }


def _bounds(envelope):
    # ST_Envelope returns a point for a degenerate box; both forms give min/max corners.
    coordinates = envelope["coordinates"]
    points = coordinates[0] if envelope["type"] == "Polygon" else [coordinates]
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


TILE_EXTENT = 4096
TILE_BUFFER = 64


def parcel_tile(z, x, y, *, namespaces=None):
    """Mapbox Vector Tile of current parcel footprints, keyed by identity only.

    Attributes stay in `parcel_features`, so drawn footprints never diverge from the
    recovery, classification and provenance rules applied to the published rows.
    """
    table = connection.ops.quote_name(Parcel._meta.db_table)
    sql = f"""
        WITH tile AS (
            SELECT ST_TileEnvelope(%s, %s, %s, margin => {TILE_BUFFER / TILE_EXTENT}) AS envelope
        ),
        shapes AS (
            SELECT ST_AsMVTGeom(
                       ST_Transform(parcel.geometry, 3857), ST_TileEnvelope(%s, %s, %s),
                       {TILE_EXTENT}, {TILE_BUFFER}, true
                   ) AS geom,
                   parcel.id::text AS id
            FROM {table} AS parcel, tile
            WHERE parcel.superseded_by_id IS NULL
              AND parcel.geometry && ST_Transform(tile.envelope, 4326)
              AND (%s::text[] IS NULL OR parcel.source_namespace = ANY(%s::text[]))
        )
        SELECT ST_AsMVT(shapes, 'parcels', {TILE_EXTENT}, 'geom') FROM shapes
        WHERE geom IS NOT NULL
    """
    names = list(namespaces) if namespaces is not None else None
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '2000ms'")
            cursor.execute(sql, [z, x, y, z, x, y, names, names])
            return bytes(cursor.fetchone()[0] or b"")


def parcel_identity(*, parcel_id, namespace=None, namespaces=None):
    records = Parcel.objects.filter(id=parcel_id)
    if namespace is not None:
        records = records.filter(source_namespace=namespace)
    if namespaces is not None:
        records = records.filter(source_namespace__in=namespaces)
    # Preserve links to a provider-renumbering duplicate without publishing it twice.
    canonical_id = records.values_list("superseded_by_id", flat=True).first()
    if canonical_id is not None:
        records = Parcel.objects.filter(id=canonical_id, superseded_by__isnull=True)
        if namespace is not None:
            records = records.filter(source_namespace=namespace)
        if namespaces is not None:
            records = records.filter(source_namespace__in=namespaces)
    return (
        records.annotate(area=Area(Cast("geometry", MultiPolygonField(srid=4326, geography=True))))
        .values(
            "id",
            "source_namespace",
            "code",
            "district",
            "community",
            "revision",
            "land_use",
            "construction_status",
            "area",
        )
        .first()
    )
