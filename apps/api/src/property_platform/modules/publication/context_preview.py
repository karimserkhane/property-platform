"""Bounded reads of complete public snapshots, never an HTTP-time collection."""

from ..evidence.abu_dhabi import FEEDS
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


def public_context(dataset, *, query="", offset=0, limit=40):
    feed = FEEDS[dataset]
    snapshot = (
        PublicContextSnapshot.objects.filter(
            dataset=dataset, territory="abu-dhabi", run__status="succeeded"
        )
        .select_related("capture")
        .order_by("-capture__fetched_at", "-created_at", "-pk")
        .first()
    )
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
    rows = MODELS[dataset].objects.filter(snapshot=snapshot)
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
        values = {"source_record_id": row.source_record_id, "name": row.name}
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
