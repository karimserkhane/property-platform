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


def map_rows(target, bbox, limit=3000, *, namespaces=None, parcel_namespaces=None):
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
        if namespaces is not None:
            records = records.filter(source_namespace__in=namespaces)
        if target == "administrative_area":
            records = records.filter(superseded_by__isnull=True)
        if target == "place":
            parcels = Parcel.objects.filter(
                geometry__covers=OuterRef("geometry"), superseded_by__isnull=True
            )
            if parcel_namespaces is not None:
                parcels = parcels.filter(source_namespace__in=parcel_namespaces)
            records = records.annotate(
                parcel_ids=ArraySubquery(parcels.order_by("id").values("id")[:20])
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


def overlapping_parcels(parcel_id, *, namespaces=None):
    """Comparable footprints, not parent sectors or a claim of cadastral supersession."""
    from django.contrib.gis.db.models.functions import Area, Intersection
    from django.db.models import F, FloatField
    from django.db.models.functions import Cast

    parcel = Parcel.objects.get(id=parcel_id, superseded_by__isnull=True)
    records = Parcel.objects.filter(
        superseded_by__isnull=True, geometry__intersects=parcel.geometry
    ).exclude(id=parcel_id)
    if namespaces is not None:
        records = records.filter(source_namespace__in=namespaces)
    # Ratios use the same local WGS84 surface on each side. No square-metre
    # measurement is inferred from degrees. Both footprints must overlap by 80%.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout='2000ms'")
        return list(
            records.annotate(
                footprint=Cast(Area("geometry"), FloatField()),
                overlap=Cast(Area(Intersection("geometry", parcel.geometry)), FloatField()),
            )
            .filter(overlap__gte=parcel.geometry.area * 0.8)
            .filter(overlap__gte=F("footprint") * 0.8)
            .order_by("code", "id")
            .values("id", "code", "land_use", "construction_status", "source_namespace")[:8]
        )


def nearby_place_rows(target, identity, *, namespaces=None, parcel_namespaces=None):
    """Indexed, bounded candidates within 1.5 km of a stored feature's centroid."""
    model = Parcel if target == "parcel" else MODELS[target]
    records = model.objects.filter(id=identity)
    if target == "parcel":
        records = records.filter(superseded_by__isnull=True)
        scope = parcel_namespaces
    else:
        records = records.filter(active=True)
        scope = namespaces
    if scope is not None:
        records = records.filter(source_namespace__in=scope)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout='3000ms'")
        center = (
            records.annotate(center=Centroid("geometry")).values_list("center", flat=True).first()
        )
        if center is None:
            return None
        places = Place.objects.filter(active=True, geometry__dwithin=(center, 0.02))
        if namespaces is not None:
            places = places.filter(source_namespace__in=namespaces)
        if target == "place":
            places = places.exclude(id=identity)
        rows = list(
            places.annotate(distance=Distance("geometry", center, spheroid=True))
            .filter(distance__lte=1500)
            .order_by("distance", "id")
            .values("id", "name", "name_ar", "kind", "distance")[:401]
        )
    return rows[:400], len(rows) > 400
