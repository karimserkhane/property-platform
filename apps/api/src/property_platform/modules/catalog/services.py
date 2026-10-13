from django.contrib.gis.geos import MultiPolygon, Polygon
from django.contrib.gis.geos.error import GEOSException

from .models import AdministrativeArea, Parcel


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


def reconcile_parcel(*, namespace, record, geometry, canonical_id=None):
    """Called inside an outer transaction that also persists evidence and audit."""
    records = Parcel.objects.select_for_update().filter(source_namespace=namespace)
    parcel = (
        records.get(id=canonical_id, superseded_by__isnull=True)
        if canonical_id is not None
        else records.filter(source_record_id=record["record_id"]).first()
    )
    if parcel is not None and parcel.superseded_by_id is not None:
        raise ValueError("Superseded parcel requires an explicit canonical identity")
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


def reconcile_map_record(*, model, namespace, record_id, values, geometry, canonical_id=None):
    records = model.objects.select_for_update().filter(source_namespace=namespace)
    if canonical_id is not None:
        if model is not AdministrativeArea:
            raise ValueError("Canonical aliases are only supported for administrative areas")
        identity = records.get(id=canonical_id, superseded_by__isnull=True)
    else:
        identity = records.filter(source_record_id=record_id).first()
    if isinstance(identity, AdministrativeArea) and identity.superseded_by_id is not None:
        raise ValueError("Superseded area requires an explicit canonical identity")
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


def supersede_parcel(*, duplicate_id, canonical_id):
    duplicate = Parcel.objects.select_for_update().get(id=duplicate_id)
    canonical = Parcel.objects.select_for_update().get(id=canonical_id)
    if (
        duplicate.id == canonical.id
        or canonical.superseded_by_id is not None
        or duplicate.superseded_by_id not in (None, canonical.id)
        or Parcel.objects.filter(superseded_by=duplicate).exists()
        or duplicate.source_namespace != canonical.source_namespace
        or not duplicate.official_plot_id
        or duplicate.official_plot_id != canonical.official_plot_id
        or duplicate.code != canonical.code
        or duplicate.municipality != canonical.municipality
        or duplicate.district != canonical.district
        or not duplicate.geometry.equals(canonical.geometry)
    ):
        raise ValueError("Unsafe parcel supersession")
    if duplicate.superseded_by_id == canonical.id:
        return False
    duplicate.superseded_by = canonical
    duplicate.revision += 1
    duplicate.save(update_fields=["superseded_by", "revision", "updated_at"])
    return True


def supersede_administrative_area(*, duplicate_id, canonical_id):
    duplicate = AdministrativeArea.objects.select_for_update().get(id=duplicate_id)
    canonical = AdministrativeArea.objects.select_for_update().get(id=canonical_id)
    if (
        duplicate.id == canonical.id
        or canonical.superseded_by_id is not None
        or duplicate.superseded_by_id not in (None, canonical.id)
        or AdministrativeArea.objects.filter(superseded_by=duplicate).exists()
        or duplicate.source_namespace != canonical.source_namespace
        or (duplicate.name, duplicate.name_ar, duplicate.kind)
        != (canonical.name, canonical.name_ar, canonical.kind)
        or not duplicate.geometry.equals(canonical.geometry)
    ):
        raise ValueError("Unsafe administrative-area supersession")
    if duplicate.superseded_by_id == canonical.id:
        return False
    duplicate.superseded_by = canonical
    duplicate.revision += 1
    duplicate.save(update_fields=["superseded_by", "revision", "updated_at"])
    return True


def restore_superseded_identity(*, model, duplicate_id, canonical_id):
    if model not in (Parcel, AdministrativeArea):
        raise ValueError("Unsupported identity restoration")
    duplicate = model.objects.select_for_update().get(id=duplicate_id)
    canonical = model.objects.select_for_update().get(id=canonical_id)
    if canonical.superseded_by_id is not None or duplicate.superseded_by_id != canonical.id:
        raise ValueError("Supersession has changed; review before reversal")
    duplicate.superseded_by = None
    duplicate.revision += 1
    duplicate.save(update_fields=["superseded_by", "revision", "updated_at"])


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
