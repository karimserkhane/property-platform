"""Reviewed source families and what each promises (A32).

No ORM or Django setting is needed here, so ingestion and the API share this module.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceFamily:
    """One reviewed family: its source keys, cadence, thresholds and Prefect deployments.

    `prefixes` are `evidence.source` key prefixes, the longest match winning.
    `deployments` are shell patterns over the deployment names of the ingestion registry.
    Thresholds count days after the latest success.
    """

    key: str
    prefixes: tuple[str, ...]
    cadence_days: int
    late_after_days: int
    review_after_days: int
    deployments: tuple[str, ...]


# Reviewed against the schedules of the ingestion registry and the runs of 9 November 2026.
# A weekly cadence gets two days of grace, for a runner restart or a retried Sunday.
FAMILIES = (
    SourceFamily(
        "developer-pages",
        ("project:", "project-acquisition:", "project-discovery:", "property:", "research:"),
        7,
        9,
        30,
        (
            "*project-details",
            "*project-discovery",
            "*project-references",
            "*property-presentations",
        ),
    ),
    SourceFamily(
        "adrec-register",
        ("project-discovery:saadiyat-island:adrec-saadiyat-register",),
        7,
        9,
        30,
        ("saadiyat-project-discovery",),
    ),
    SourceFamily(
        "adrec-market", ("adrec:market-data",), 7, 9, 30, ("adrec-*-sales", "adrec-price-indices")
    ),
    SourceFamily(
        "parcels-onwani", ("dmt:onwani:smarthub",), 7, 9, 30, ("parcels-onwani", "*-parcels-onwani")
    ),
    # Started by hand, one long campaign at a time (F01): no weekly promise to keep.
    SourceFamily("parcels-adsdi", ("ad-sdi:",), 90, 100, 180, ("*-parcels-adsdi*",)),
    SourceFamily(
        "osm",
        ("osm:",),
        7,
        9,
        30,
        ("map-osm", "saadiyat-map-osm", "maryah-map-osm", "*-osm-bootstrap"),
    ),
    SourceFamily("overture", ("overture:",), 7, 9, 30, ("*-places-overture",)),
    SourceFamily(
        "public-context",
        ("adek:", "admobility:", "doh:", "scad:", "dmt:onwani:"),
        7,
        9,
        30,
        ("abu-dhabi-*", "map-district", "map-community", "map-street", "*-map-district"),
    ),
    SourceFamily(
        "sentinel-2", ("sentinel-2-l2a-earth-search",), 31, 35, 90, ("construction-activity",)
    ),
    SourceFamily("evidence-search", ("evidence-search-index",), 1, 2, 7, ("evidence-search",)),
)


def family_of(source_key):
    matches = [
        (len(prefix), family)
        for family in FAMILIES
        for prefix in family.prefixes
        if source_key.startswith(prefix)
    ]
    return max(matches, key=lambda match: match[0])[1] if matches else None
