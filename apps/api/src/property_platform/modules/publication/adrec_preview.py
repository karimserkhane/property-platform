"""Read only the newest complete provider snapshot; never add overlapping snapshots."""

from django.db.models import Max

from property_platform.modules.evidence import adrec
from property_platform.modules.evidence.models import AdrecMarketSnapshot


def market(territory, *, query="", offset=0, limit=40):
    base = AdrecMarketSnapshot.objects.filter(run__status__in=["succeeded", "quarantined"])
    snapshot = (
        base.filter(dataset="sales", territory=territory)
        .order_by("-period_end", "-created_at", "-pk")
        .first()
    )
    rows, count = [], 0
    if snapshot:
        sales = snapshot.sales.all()
        if query:
            sales = sales.filter(project_name__icontains=query)
        count = sales.count()
        for row in sales.order_by("-registration_date", "source_position")[offset : offset + limit]:
            rows.append(
                {
                    "position": row.source_position,
                    "registration_date": row.registration_date,
                    "project_name": row.project_name,
                    "district": row.district,
                    "community": row.community,
                    "property_type": row.property_type,
                    "property_layout": row.property_layout,
                    "sale_application_type": row.sale_application_type,
                    "sale_sequence": row.sale_sequence,
                    **{
                        field: str(getattr(row, field)) if getattr(row, field) is not None else None
                        for field in (
                            "price_aed",
                            "sold_area_sqm",
                            "plot_area_sqm",
                            "rate_aed_per_sqm",
                            "sold_share",
                        )
                    },
                }
            )
    indices, review = [], False
    index_snapshot = (
        base.filter(dataset="indices", territory="abu-dhabi").order_by("-created_at", "-pk").first()
    )
    if index_snapshot:
        review = index_snapshot.indices.filter(usable=False).exists()
        usable = index_snapshot.indices.filter(
            usable=True, kind="sale", municipality="Abu Dhabi City", zone_label="(all zones)"
        )
        period = usable.aggregate(latest=Max("period_end"))["latest"]
        seen = set()
        for row in usable.filter(period_end=period).order_by(
            "kind", "property_type", "source_position"
        ):
            # Identical duplicate index values may be displayed once; sales retain multiplicity.
            key = (row.kind, row.property_type)
            if key in seen:
                continue
            seen.add(key)
            indices.append(
                {
                    "kind": row.kind,
                    "property_type": row.property_type,
                    "period_end": row.period_end,
                    "municipality": row.municipality,
                    "index_value": str(row.index_value) if row.index_value is not None else None,
                }
            )
    return {
        "snapshot_id": snapshot.pk if snapshot else None,
        "period_start": snapshot.period_start if snapshot else None,
        "period_end": snapshot.period_end if snapshot else None,
        "retrieved_at": snapshot.run.captures.aggregate(latest=Max("fetched_at"))["latest"]
        if snapshot
        else None,
        "source_url": adrec.PAGE_URL,
        "total": count,
        "offset": offset,
        "has_more": offset + len(rows) < count,
        "sales": rows,
        "indices": indices,
        "index_review_needed": review,
    }
