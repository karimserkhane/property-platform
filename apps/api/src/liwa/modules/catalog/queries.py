"""Bounded catalogue reads; delivery code never serializes a model directly."""

import json

from django.contrib.gis.db.models.functions import Area, AsGeoJSON, Transform
from django.contrib.gis.geos import Polygon
from django.db import connection, transaction

from .models import Parcel


def parcel_features(*, namespace, bbox, limit, query=""):
    envelope = Polygon.from_bbox(bbox)
    envelope.srid = 4326
    records = Parcel.objects.filter(source_namespace=namespace, geometry__intersects=envelope)
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


def parcel_identity(*, namespace, parcel_id):
    return (
        Parcel.objects.filter(source_namespace=namespace, id=parcel_id)
        .annotate(area=Area(Transform("geometry", 32640)))
        .values(
            "id",
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
