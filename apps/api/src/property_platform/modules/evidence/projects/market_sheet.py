"""Recorded ADREC sales of a project, by type, for its sheet (C01).

Read-only. Sales are selected by the project's active reviewed labels, inside the newest
succeeded sales snapshot of the project's own territory: snapshots are overlapping 90-day
windows of the same register, so two of them are never added. Each group gives a range
and its count, never a single value; a sale of a partial share keeps its count but stays
out of the price ranges.
"""

from decimal import Decimal

from django.db.models import Count, Max, Min, Q

from ..models import AdrecMarketSnapshot, AdrecSaleObservation
from ..project_models import ProjectMarketLabel
from ..sources import adrec

SOURCE_NAME = "Abu Dhabi Real Estate Centre (ADREC)"
GROUP = ("property_type", "property_layout", "sale_application_type", "sale_sequence")
FULL_SHARE = Q(sold_share=Decimal(1))


def _range(row, field):
    low, high = row[f"{field}_min"], row[f"{field}_max"]
    return None if low is None else {"min": str(low), "max": str(high)}


def _latest_snapshot(territory_id):
    return (
        AdrecMarketSnapshot.objects.filter(
            dataset="sales", territory=territory_id, run__status="succeeded"
        )
        .order_by("-period_end", "-created_at", "-pk")
        .first()
    )


def project_market(project):
    """Sales ranges of the project's labels in the latest window; None without a label."""
    labels = list(
        ProjectMarketLabel.objects.filter(project=project, active=True).order_by(
            "district", "label"
        )
    )
    if not labels:
        return None
    snapshot = (
        _latest_snapshot(project.territory_id) if project.territory_id in adrec.DISTRICTS else None
    )
    groups, captures = [], []
    if snapshot is not None:
        selected = Q()
        for label in labels:
            selected |= Q(district=label.district, project_name=label.label)
        sales = AdrecSaleObservation.objects.filter(selected, snapshot=snapshot)
        priced = FULL_SHARE & Q(price_aed__isnull=False)
        rows = (
            sales.values(*GROUP)
            .annotate(
                sales_count=Count("pk"),
                full_share_count=Count("pk", filter=FULL_SHARE),
                price_aed_min=Min("price_aed", filter=priced),
                price_aed_max=Max("price_aed", filter=priced),
                rate_aed_per_sqm_min=Min("rate_aed_per_sqm", filter=FULL_SHARE),
                rate_aed_per_sqm_max=Max("rate_aed_per_sqm", filter=FULL_SHARE),
                sold_area_sqm_min=Min("sold_area_sqm", filter=FULL_SHARE),
                sold_area_sqm_max=Max("sold_area_sqm", filter=FULL_SHARE),
                first_registration_date=Min("registration_date"),
                last_registration_date=Max("registration_date"),
            )
            .order_by(*GROUP)
        )
        groups = [
            {
                **{field: row[field] for field in GROUP},
                "sales_count": row["sales_count"],
                "full_share_count": row["full_share_count"],
                "price_aed": _range(row, "price_aed"),
                "rate_aed_per_sqm": _range(row, "rate_aed_per_sqm"),
                "sold_area_sqm": _range(row, "sold_area_sqm"),
                "first_registration_date": row["first_registration_date"],
                "last_registration_date": row["last_registration_date"],
            }
            for row in rows
        ]
        captures = [
            {"url": url, "content_sha256": digest}
            for url, digest in sales.values_list("capture__url", "capture__content_sha256")
            .distinct()
            .order_by("capture__url", "capture__content_sha256")
        ]
    return {
        "source": {"name": SOURCE_NAME, "url": adrec.PAGE_URL},
        "labels": [
            {
                "district": label.district,
                "label": label.label,
                "evidence": label.evidence,
                "registration_number": label.registration_number or None,
                "reviewed_on": label.reviewed_on,
            }
            for label in labels
        ],
        "window": None
        if snapshot is None
        else {
            "territory": snapshot.territory,
            "period_start": snapshot.period_start,
            "period_end": snapshot.period_end,
            "collected_at": snapshot.created_at,
            "captures": captures,
        },
        "groups": groups,
    }
