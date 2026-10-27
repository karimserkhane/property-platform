import json

from django.contrib.gis.db.models.functions import AsGeoJSON, Centroid, Distance, Envelope
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


def map_rows(target, bbox, limit=3000, *, namespaces=None, parcel_namespaces=None, geometry=True):
    """Active features of a family in a bbox. Without geometry, rows carry their bounds
    instead, for clients drawing streets and buildings from `context_tile`."""
    from django.contrib.gis.geos import Polygon

    from .queries import _bounds

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
        if geometry:
            records = records.annotate(shape=AsGeoJSON("geometry", precision=6))
        else:
            records = records.annotate(shape=AsGeoJSON(Envelope("geometry"), precision=6))
        rows = list(records.order_by("id").values(*fields)[: limit + 1])
    for row in rows:
        shape = json.loads(row.pop("shape"))
        if geometry:
            row["geometry"] = shape
        else:
            row["bounds"] = _bounds(shape)
    return rows[:limit], len(rows) > limit


CONTEXT_TILE_LAYERS = {"building": Building, "street": Street}


def context_tile(z, x, y, *, namespaces=None):
    """Mapbox Vector Tile of active buildings and streets, keyed by identity.

    Heights, uses and provenance stay in `map_rows` and the published context
    index, as for parcel tiles. Streets also carry their display names: labels
    placed along a line read tile properties and cannot use feature state.
    Overview zooms omit sub-pixel buildings.
    """
    from .queries import DETAIL_ZOOM, MERCATOR_WORLD_M, TILE_BUFFER, TILE_EXTENT

    layers, params = [], []
    names = list(namespaces) if namespaces is not None else None
    min_area = (MERCATOR_WORLD_M / (512 * 2**z)) ** 2 / 2
    for layer, model in CONTEXT_TILE_LAYERS.items():
        table = connection.ops.quote_name(model._meta.db_table)
        sized = "AND (%s OR ST_Area(ST_Transform(item.geometry, 3857)) >= %s)"
        layers.append(
            f"""
            (SELECT COALESCE(ST_AsMVT(shapes, '{layer}', {TILE_EXTENT}, 'geom'), '')
             FROM (
                SELECT ST_AsMVTGeom(
                           ST_Transform(item.geometry, 3857), ST_TileEnvelope(%s, %s, %s),
                           {TILE_EXTENT}, {TILE_BUFFER}, true
                       ) AS geom,
                       item.id::text AS id{", item.name, item.name_ar" if model is Street else ""}
                FROM {table} AS item
                WHERE item.active
                  AND item.geometry && ST_Transform(
                      ST_TileEnvelope(%s, %s, %s, margin => {TILE_BUFFER / TILE_EXTENT}), 4326
                  )
                  AND (%s::text[] IS NULL OR item.source_namespace = ANY(%s::text[]))
                  {sized if model is Building else ""}
             ) AS shapes
             WHERE geom IS NOT NULL)
            """
        )
        params += [z, x, y, z, x, y, names, names]
        if model is Building:
            params += [z >= DETAIL_ZOOM, min_area]
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '2000ms'")
            cursor.execute("SELECT " + " || ".join(layers), params)
            return bytes(cursor.fetchone()[0] or b"")


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
            places.annotate(
                distance=Distance("geometry", center, spheroid=True),
                shape=AsGeoJSON("geometry", precision=8),
            )
            .filter(distance__lte=1500)
            .order_by("distance", "id")
            .values("id", "name", "name_ar", "kind", "distance", "source_namespace", "shape")[:401]
        )
    for row in rows:
        row["geometry"] = json.loads(row.pop("shape"))
    return rows[:400], len(rows) > 400


PROJECT_MARKER_RADIUS_M = 50


def project_markers_near_parcels(
    parcel_ids, radius_m=PROJECT_MARKER_RADIUS_M, excluded_namespaces=()
):
    """Active project marker points within `radius_m` of each parcel boundary (0 inside).

    Clients keep their own naming and ambiguity rules; this only replaces the boundary
    distance they used to compute from the full parcel geometry. Markers of
    `excluded_namespaces` (sources the publication layer withholds) are left out.
    """
    if not parcel_ids:
        return {}
    parcels = connection.ops.quote_name(Parcel._meta.db_table)
    places = connection.ops.quote_name(Place._meta.db_table)
    # A planar prefilter about 1.3 times the radius at UAE latitudes keeps the GiST index.
    margin = radius_m * 1.3 / 111_320
    sql = f"""
        SELECT parcel.id::text, place.id::text,
               ST_Distance(parcel.geometry::geography, place.geometry::geography)
        FROM {parcels} AS parcel
        JOIN {places} AS place
          ON place.active
         AND place.kind LIKE %s
         AND place.source_namespace <> ALL(%s::text[])
         AND place.geometry && ST_Expand(parcel.geometry, %s)
         AND ST_DWithin(parcel.geometry::geography, place.geometry::geography, %s)
        WHERE parcel.id = ANY(%s::uuid[])
        ORDER BY parcel.id, 3, place.id
    """
    nearby = {}
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout='3000ms'")
            cursor.execute(
                sql,
                [
                    r"%\_project\_marker",
                    list(excluded_namespaces),
                    margin,
                    radius_m,
                    list(parcel_ids),
                ],
            )
            for parcel_id, place_id, distance in cursor.fetchall():
                nearby.setdefault(parcel_id, []).append(
                    {"place_id": place_id, "distance_m": round(distance, 2)}
                )
    return nearby
