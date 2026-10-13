import json

from django.contrib.gis.db.models.functions import AsGeoJSON, Centroid, Distance
from django.contrib.postgres.expressions import ArraySubquery
from django.db import connection, transaction
from django.db.models import OuterRef

from .models import AdministrativeArea, Building, Parcel, Place, Street

MODELS = {
    "street": Street,
    "building": Building,
    "place": Place,
    "administrative_area": AdministrativeArea,
}


def map_rows(target, bbox, limit=3000):
    from django.contrib.gis.geos import Polygon

    envelope = Polygon.from_bbox(bbox)
    envelope.srid = 4326
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout='3000ms'")
        model = MODELS[target]
        fields = ["id", "name", "name_ar", "kind", "source_namespace", "shape"]
        if target == "building":
            fields += ["height_m", "levels"]
        records = model.objects.filter(active=True, geometry__intersects=envelope)
        if target == "administrative_area":
            records = records.filter(superseded_by__isnull=True)
        if target == "place":
            records = records.annotate(
                parcel_ids=ArraySubquery(
                    Parcel.objects.filter(
                        geometry__covers=OuterRef("geometry"), superseded_by__isnull=True
                    )
                    .order_by("id")
                    .values("id")[:20]
                )
            )
            fields += ["parcel_ids"]
        rows = list(
            records.order_by("id")
            .annotate(shape=AsGeoJSON("geometry", precision=6))
            .values(*fields)[: limit + 1]
        )
    for row in rows:
        row["geometry"] = json.loads(row.pop("shape"))
    return rows[:limit], len(rows) > limit


def parcel_surroundings(parcel_id):
    parcel = Parcel.objects.annotate(center=Centroid("geometry")).get(id=parcel_id)
    places = list(
        Place.objects.filter(active=True, geometry__coveredby=parcel.geometry)
        .order_by("name")
        .values("id", "name", "name_ar", "kind")[:40]
    )
    center = parcel.center
    streets = list(
        # Cheap indexed prefilter, conservatively wider than 120 m throughout the UAE.
        Street.objects.filter(active=True, geometry__dwithin=(center, 0.002))
        .annotate(distance=Distance("geometry", center, spheroid=True))
        .filter(distance__lte=120)
        .order_by("distance")
        .values("id", "name", "name_ar", "distance")[:8]
    )
    return places, streets
