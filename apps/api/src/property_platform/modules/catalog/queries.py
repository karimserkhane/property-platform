"""Bounded catalogue reads; delivery code never serializes a model directly."""

import json

from django.contrib.gis.db.models import MultiPolygonField
from django.contrib.gis.db.models.functions import Area, AsGeoJSON
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


def parcel_features(*, bbox, limit, query="", namespace=None, namespaces=None, after=None):
    envelope = Polygon.from_bbox(bbox)
    envelope.srid = 4326
    records = Parcel.objects.filter(geometry__intersects=envelope, superseded_by__isnull=True)
    if namespace is not None:
        records = records.filter(source_namespace=namespace)
    if namespaces is not None:
        records = records.filter(source_namespace__in=namespaces)
    if after is not None:
        records = records.filter(id__gt=after)
    if query:
        records = records.filter(code__istartswith=query)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '2000ms'")
        rows = list(
            records.order_by("id")
            .annotate(shape=AsGeoJSON("geometry", precision=6))
            .values("id", "code", "community", "land_use", "construction_status", "shape")[
                : limit + 1
            ]
        )
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": str(row["id"]),
                "geometry": json.loads(row["shape"]),
                "properties": {
                    "id": str(row["id"]),
                    "code": row["code"],
                    "community": row["community"],
                    "land_use": row["land_use"],
                    "construction_status": row["construction_status"],
                },
            }
            for row in rows[:limit]
        ],
        "truncated": len(rows) > limit,
        "next_cursor": str(rows[limit - 1]["id"]) if len(rows) > limit else None,
    }


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
