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
            Parcel.objects.filter(source_namespace__in=namespaces)
            .values("source_namespace")
            .annotate(count=Count("id"))
            .values_list("source_namespace", "count")
        )


def parcel_features(*, bbox, limit, query="", namespace=None, namespaces=None):
    envelope = Polygon.from_bbox(bbox)
    envelope.srid = 4326
    records = Parcel.objects.filter(geometry__intersects=envelope)
    if namespace is not None:
        records = records.filter(source_namespace=namespace)
    if namespaces is not None:
        records = records.filter(source_namespace__in=namespaces)
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
    }


def parcel_identity(*, parcel_id, namespace=None, namespaces=None):
    records = Parcel.objects.filter(id=parcel_id)
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
