"""Bounded reads of complete public snapshots, never an HTTP-time collection."""

from ..evidence.abu_dhabi import FEEDS
from ..evidence.history import context_rows, observation_history
from ..evidence.models import (
    BusRouteObservation,
    CensusMeasureObservation,
    DistrictBoundaryObservation,
    HealthFacilityObservation,
    PublicContextSnapshot,
    SchoolObservation,
)

MODELS = {
    "districts": DistrictBoundaryObservation,
    "health": HealthFacilityObservation,
    "schools": SchoolObservation,
    "mobility": BusRouteObservation,
    "statistics": CensusMeasureObservation,
}


def latest_context_snapshot(dataset):
    return (
        PublicContextSnapshot.objects.filter(
            dataset=dataset, territory="abu-dhabi", run__status="succeeded"
        )
        .select_related("capture")
        .order_by("-capture__fetched_at", "-created_at", "-pk")
        .first()
    )


def public_context(dataset, *, query="", offset=0, limit=40):
    feed = FEEDS[dataset]
    snapshot = latest_context_snapshot(dataset)
    result = {
        "dataset": dataset,
        "territory": "abu-dhabi",
        "snapshot_id": snapshot.pk if snapshot else None,
        "retrieved_at": snapshot.capture.fetched_at if snapshot else None,
        "acquisition_method": snapshot.capture.acquisition_method if snapshot else None,
        "timestamp_basis": snapshot.capture.timestamp_basis if snapshot else None,
        "source_modified_date": snapshot.source_modified_date if snapshot else None,
        "source_url": feed.page_url,
        "reuse_status": feed.reuse_status,
        "total": 0,
        "offset": offset,
        "has_more": False,
        "health": [],
        "districts": [],
        "schools": [],
        "mobility": [],
        "statistics": [],
    }
    if not snapshot:
        return result
    rows = context_rows(MODELS[dataset], dataset)
    if query:
        from django.db.models import Q

        search = Q(name__icontains=query)
        if dataset in {"schools", "districts"}:
            search |= Q(name_ar__icontains=query) | Q(municipality__icontains=query)
            if dataset == "schools":
                search |= Q(district__icontains=query)
        elif dataset == "mobility":
            search |= (
                Q(origin__icontains=query)
                | Q(destination__icontains=query)
                | Q(number__iexact=query)
            )
        elif dataset == "health":
            search |= Q(address__icontains=query) | Q(facility_type__icontains=query)
        rows = rows.filter(search)
    result["total"] = rows.count()
    result["has_more"] = offset + limit < result["total"]
    for row in rows.order_by("name", "source_record_id")[offset : offset + limit]:
        values = {
            "source_record_id": row.source_record_id,
            "name": row.name,
            **observation_history(row, snapshot),
        }
        if dataset == "districts":
            values.update(
                name_ar=row.name_ar,
                municipality=row.municipality,
                district_id=row.district_id,
                bounds=row.geometry.extent,
            )
        elif dataset == "health":
            values.update(
                facility_type=row.facility_type,
                address=row.address,
                planned=row.planned,
                operator=row.operator,
                licence_number=row.licence_number,
                services_original=row.services_original,
                longitude=row.location.x,
                latitude=row.location.y,
            )
        elif dataset == "schools":
            values.update(
                name_ar=row.name_ar,
                municipality=row.municipality,
                district=row.district,
                district_ar=row.district_ar,
                community=row.community,
                grades_original=row.grades_original,
                longitude=row.location.x,
                latitude=row.location.y,
            )
        elif dataset == "mobility":
            values.update(
                number=row.number,
                origin=row.origin,
                destination=row.destination,
                timetable_url=row.timetable_url,
            )
        else:
            values.update(
                reference_year=row.reference_year,
                region=row.region,
                category=row.category,
                unit=row.unit,
                value=str(row.value),
                rounding_base=row.rounding_base,
            )
        result[dataset].append(values)
    return result


def district_map():
    """Provider boundaries for navigation, not canonical city/property identity.

    Simplification is a derived display shape in metres; original evidence,
    bounds and the interior label point retain their unmodified geometry.
    """
    import json

    from django.contrib.gis.geos import MultiPolygon

    from ..evidence.collection_profiles import COLLECTIONS

    snapshot = latest_context_snapshot("districts")
    result = {
        "type": "FeatureCollection",
        "territory": "abu-dhabi",
        "snapshot_id": snapshot.pk if snapshot else None,
        "retrieved_at": snapshot.capture.fetched_at if snapshot else None,
        "source_url": FEEDS["districts"].page_url,
        "display_geometry_version": "district-navigation-20m-v1",
        "features": [],
    }
    if not snapshot:
        return result
    rows = list(
        context_rows(DistrictBoundaryObservation, "districts").order_by(
            "municipality", "name", "source_record_id"
        )[:501]
    )
    if len(rows) > 500:
        raise ValueError("District navigation exceeds reviewed response budget")
    profiles = {("ADM", profile.district_id): profile.territory for profile in COLLECTIONS.values()}
    for row in rows:
        history = observation_history(row, snapshot)
        shape = row.geometry.clone()
        shape.transform(3857)
        shape = shape.simplify(20, preserve_topology=True)
        shape.transform(4326)
        if shape.geom_type == "Polygon":
            shape = MultiPolygon(shape, srid=4326)
        point = row.geometry.point_on_surface
        result["features"].append(
            {
                "type": "Feature",
                "id": row.source_record_id,
                "geometry": json.loads(shape.geojson),
                "properties": {
                    "source_record_id": row.source_record_id,
                    "district_id": row.district_id,
                    "name": row.name,
                    "name_ar": row.name_ar,
                    "municipality": row.municipality,
                    "bounds": row.geometry.extent,
                    "label_point": [point.x, point.y],
                    "explore_territory_id": profiles.get((row.municipality, row.district_id)),
                    **history,
                },
            }
        )
    return result
