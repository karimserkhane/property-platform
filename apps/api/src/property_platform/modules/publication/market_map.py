"""District-level sales analysis; no guessed project coordinates or transaction deduplication."""

from collections import defaultdict
from decimal import Decimal
from statistics import median

from ..evidence.models import AdrecMarketSnapshot
from .adrec_preview import market
from .context_preview import district_map


def district_market(territory, *, query="", snapshot_id=None):
    snapshot = market(territory, query=query, limit=1, snapshot_id=snapshot_id)
    districts = district_map()

    def normalise(value):
        return " ".join(value.casefold().split())

    locations = defaultdict(list)
    for feature in districts["features"]:
        locations[normalise(feature["properties"]["name"])].append(feature)
    result = {
        "type": "FeatureCollection",
        "features": [],
        "snapshot_id": snapshot["snapshot_id"],
        "boundary_snapshot_id": districts["snapshot_id"],
        "period_start": snapshot["period_start"],
        "period_end": snapshot["period_end"],
        "source_url": snapshot["source_url"],
        "boundary_source_url": districts["source_url"],
        "unmatched_sales": 0,
        "mapped_sales": 0,
        "historical": snapshot["historical"],
    }
    if not snapshot["snapshot_id"]:
        return result
    sales = AdrecMarketSnapshot.objects.get(pk=snapshot["snapshot_id"]).sales.all()
    if query:
        sales = sales.filter(project_name__icontains=query)
    if sales.count() > 50000:
        raise ValueError("Market mapping row budget exceeded")
    grouped = defaultdict(list)
    for district, price, rate in sales.values_list("district", "price_aed", "rate_aed_per_sqm"):
        grouped[normalise(district)].append((price, rate))
    for district, rows in grouped.items():
        candidates = locations.get(district, [])
        if len(candidates) != 1:
            result["unmatched_sales"] += len(rows)
            continue
        feature = candidates[0]
        rates = [rate for _, rate in rows if rate is not None and rate > 0]
        # Rates reflect the provider's mixed property population, never a valuation.
        result["features"].append(
            {
                "type": "Feature",
                "id": feature["id"],
                "geometry": feature["geometry"],
                "properties": {
                    "name": feature["properties"]["name"],
                    "name_ar": feature["properties"]["name_ar"],
                    "sales": len(rows),
                    "rate_samples": len(rates),
                    "median_rate": str(median(rates)) if len(rates) >= 5 else None,
                    "volume_aed": str(
                        sum((price for price, _ in rows if price is not None), Decimal(0))
                    ),
                    "boundary_ingested_at": feature["properties"]["ingested_at"],
                },
            }
        )
        result["mapped_sales"] += len(rows)
    return result
