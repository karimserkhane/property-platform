from django.contrib.gis.geos import MultiPolygon, Polygon
from django.contrib.gis.geos.error import GEOSException

from .models import Parcel


def geometry_from_rings(rings):
    """Preserve disjoint shells and holes, reject rather than silently repair."""
    try:
        polygons = [Polygon(ring, srid=4326) for ring in rings]
    except (GEOSException, TypeError, ValueError) as exc:
        raise ValueError("Invalid polygon ring") from exc
    if not polygons or any(not p.valid or p.empty for p in polygons):
        raise ValueError("Invalid polygon ring")
    depths = [sum(other.contains(p) for other in polygons if other is not p) for p in polygons]
    shells = []
    for i, polygon in enumerate(polygons):
        if depths[i] % 2:
            continue
        holes = [
            other.coords[0]
            for j, other in enumerate(polygons)
            if depths[j] == depths[i] + 1 and polygon.contains(other)
        ]
        shells.append(Polygon(polygon.coords[0], *holes, srid=4326))
    geometry = MultiPolygon(*shells, srid=4326)
    if not geometry.valid or geometry.empty:
        raise ValueError("Invalid multipolygon")
    return geometry


def reconcile_parcel(*, namespace, record, geometry):
    """Called inside an outer transaction that also persists evidence and audit."""
    parcel = (
        Parcel.objects.select_for_update()
        .filter(source_namespace=namespace, source_record_id=record["record_id"])
        .first()
    )
    values = record["values"]
    if parcel is None:
        parcel = Parcel.objects.create(
            source_namespace=namespace,
            source_record_id=record["record_id"],
            geometry=geometry,
            **values,
        )
        return parcel, "created", {}, values
    before = {key: getattr(parcel, key) for key in values}
    geometry_changed = not parcel.geometry.equals_exact(geometry, 0)
    if before == values and not geometry_changed:
        return parcel, "unchanged", {}, {}
    for key, value in values.items():
        setattr(parcel, key, value)
    parcel.geometry = geometry
    parcel.revision += 1
    parcel.save()
    return parcel, "updated", {**before, "geometry_changed": geometry_changed}, values


def reconcile_map_record(*, model, namespace, record_id, values, geometry):
    identity = (
        model.objects.select_for_update()
        .filter(source_namespace=namespace, source_record_id=record_id)
        .first()
    )
    if identity is None:
        identity = model.objects.create(
            source_namespace=namespace, source_record_id=record_id, geometry=geometry, **values
        )
        return identity, "created", {}, values
    before = {key: getattr(identity, key) for key in values}
    changed = not identity.geometry.equals_exact(geometry, 0)
    if before == values and not changed and identity.active:
        return identity, "unchanged", {}, {}
    for key, value in values.items():
        setattr(identity, key, value)
    identity.geometry = geometry
    identity.active = True
    identity.revision += 1
    identity.save()
    return identity, "updated", {**before, "geometry_changed": changed}, values


def retire_map_record(*, model, namespace, record_id):
    identity = (
        model.objects.select_for_update()
        .filter(
            source_namespace=namespace,
            source_record_id=record_id,
            active=True,
        )
        .first()
    )
    if identity is None:
        return None
    identity.active = False
    identity.revision += 1
    identity.save(update_fields=["active", "revision", "updated_at"])
    return identity
