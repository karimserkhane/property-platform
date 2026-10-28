"""Explicit deployed datasets. Registering a territory never invents its data."""

import hashlib
import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Literal, get_args

from property_platform.modules.evidence.collection_profiles import DEFAULT_TERRITORY, collection_for

TERRITORY = DEFAULT_TERRITORY
Territory = Literal["al-reem-island", "saadiyat-island", "al-maryah-island"]
TERRITORIES = get_args(Territory)
TIMEZONE = "Asia/Dubai"


@dataclass(frozen=True)
class Dataset:
    name: str
    flow_name: str
    description: str
    parameters: dict
    cron: str | None


DATASETS = (
    Dataset(
        "parcels-onwani",
        "property-platform-parcels",
        "Official parcels; invalid geometries stay in quarantine.",
        {},
        "0 3 * * 0",
    ),
    *(
        Dataset(
            f"map-{layer}",
            "property-platform-map",
            f"Source-defined {layer} layer; no commercial identity reconciliation.",
            {"layer": layer},
            f"{minute} 4 * * 0",
        )
        for layer, minute in (("district", 0), ("community", 15), ("street", 30), ("osm", 45))
    ),
    Dataset(
        "project-references",
        "property-platform-references",
        "Reviewed public research URLs and declared project points, not accepted facts.",
        {"limit": 200, "reference_key": None},
        "0 5 * * 1",
    ),
    Dataset(
        "property-presentations",
        "property-platform-presentations",
        "Refresh reviewed presentations and licensed images; no price/inventory extraction.",
        {},
        "0 2 * * *",
    ),
    Dataset(
        "project-details",
        "property-platform-project-details",
        "Refresh Reem projects independently, retaining evidence and document links.",
        {},
        "0 2 * * 6",
    ),
    Dataset(
        "sentinel-previews",
        "property-platform-imagery",
        "Manual import of two historical Sentinel snapshots from an acquired receipt.",
        {"receipt_name": "sentinel-reem.json"},
        None,
    ),
    Dataset(
        "ingestion-readiness",
        "property-platform-readiness",
        "Check source registries and orchestration schema without collecting or writing.",
        {},
        None,
    ),
    Dataset(
        "media-storage",
        "property-platform-media-storage",
        "Resume private archival of acquired licensed photos; never publish to the CDN.",
        {},
        None,
    ),
)


DATASETS += tuple(
    Dataset(
        f"basemap-{provider}",
        "property-platform-basemap-archive",
        "Archive demanded/covered tiles with exact acquisition times; preserve every version.",
        {"provider": provider},
        "* * * * *",
    )
    for provider in ("openfreemap", "sentinel-worldcover-2020", "sentinel-worldcover-2021")
)
DATASETS += (
    Dataset(
        "empty-project-catalogue-rebuild",
        "property-platform-project-rebuild",
        "Explicit schema initialization and preserved source replay into an empty catalogue.",
        {"mode": "archive", "include_geography": False},
        None,
    ),
    Dataset(
        "source-rights",
        "property-platform-source-rights",
        "Mirror the reviewed source rights (licence, collection, publication) into the database.",
        {},
        "45 0 * * *",
    ),
    Dataset(
        "data-history",
        "property-platform-data-history",
        "Verify every owned table has a pipeline owner and database audit; retain the report.",
        {},
        "0 1 * * *",
    ),
    Dataset(
        "backup-database",
        "property-platform-backup",
        "Snapshot dump, private file mirror and retention under BACKUP_DIR; never in Git.",
        {},
        "30 1 * * *",
    ),
    Dataset(
        "rebuild-check",
        "property-platform-rebuild-check",
        "Replay source captures in a disposable database and compare every owned table; "
        "no live collection.",
        {},
        None,
    ),
    Dataset(
        "restore-check",
        "property-platform-restore-check",
        "Restore the newest dump into a throwaway database and compare its row counts.",
        {},
        "0 5 * * 0",
    ),
)

# Same reviewed connectors, distinct source identities and deployment scopes.
DATASETS += (
    Dataset(
        "routing-osm-graph",
        "property-platform-routing-graph",
        "Archive OSM inputs and build the local walking network; retain earlier graphs.",
        {},
        "0 3 1 * *",
    ),
    Dataset(
        "walking-areas",
        "property-platform-walking-areas",
        "Compute and archive queued walking areas, with source graph and exact ingestion time.",
        {},
        "* * * * *",
    ),
    Dataset(
        "construction-activity",
        "property-platform-construction-activity",
        "Sentinel-2 ground change of reviewed project parcels; a dated signal, never progress.",
        {"territory": "all"},
        "0 4 5 * *",
    ),
)

# Same reviewed connectors, distinct source identities and deployment scopes.
DATASETS += (
    *(
        Dataset(
            f"{prefix}-places-overture",
            "property-platform-map",
            "Bounded Overture Places release; independent evidence, no project identity inference.",
            {"territory": territory, "layer": "overture"},
            f"{minute} 9 * * 0",
        )
        for prefix, territory, minute in (
            ("reem", "al-reem-island", 0),
            ("saadiyat", "saadiyat-island", 30),
            ("maryah", "al-maryah-island", 45),
        )
    ),
    Dataset(
        "reem-osm-bootstrap",
        "property-platform-osm-bootstrap",
        "Manual bounded official OSM API acquisition for Reem; no recurring schedule.",
        {"territory": "al-reem-island"},
        None,
    ),
    Dataset(
        "reem-project-discovery",
        "property-platform-project-discovery",
        "Observe official catalogues; new links remain review candidates, never map identities.",
        {"territory": "al-reem-island"},
        "0 4 * * 6",
    ),
    Dataset(
        "saadiyat-project-discovery",
        "property-platform-project-discovery",
        "Observe Saadiyat publisher catalogues with exact source receipts and review candidates.",
        {"territory": "saadiyat-island"},
        "30 4 * * 6",
    ),
    Dataset(
        "project-media-files",
        "property-platform-project-media-files",
        "Manual private operator manifest: image/PDF/video/GLB files, no approval or publication.",
        {},
        None,
    ),
    Dataset(
        "abu-dhabi-districts",
        "property-platform-public-context",
        "Complete Onwani district boundaries for ADM, AAM and WRM; source identities preserved.",
        {"territory": "abu-dhabi", "dataset": "districts"},
        "0 12 * * 0",
    ),
    Dataset(
        "saadiyat-property-presentations",
        "property-platform-presentations",
        "Reviewed Park View profiles; no unlicensed promoter photographs.",
        {"territory": "saadiyat-island"},
        "30 8 * * 0",
    ),
    Dataset(
        "saadiyat-project-details",
        "property-platform-project-details",
        "Refresh Saadiyat projects independently, retaining evidence and document links.",
        {"territory": "saadiyat-island"},
        "0 3 * * 6",
    ),
    Dataset(
        "saadiyat-osm-bootstrap",
        "property-platform-osm-bootstrap",
        "Manual bounded OSM API acquisition for initial Saadiyat coverage; no recurring schedule.",
        {"territory": "saadiyat-island"},
        None,
    ),
    Dataset(
        "saadiyat-parcels-onwani",
        "property-platform-parcels",
        "Official Saadiyat parcels, with captures and quarantine.",
        {"territory": "saadiyat-island"},
        "0 6 * * 0",
    ),
    *(
        Dataset(
            f"saadiyat-map-{layer}",
            "property-platform-map",
            f"Saadiyat {layer}; source identities remain separate from Reem.",
            {"territory": "saadiyat-island", "layer": layer},
            f"{minute} 7 * * 0",
        )
        for layer, minute in (("district", 0), ("community", 15), ("street", 30), ("osm", 45))
    ),
    Dataset(
        "saadiyat-project-references",
        "property-platform-references",
        "Reviewed official Saadiyat research sources, not verified inventory.",
        {"territory": "saadiyat-island", "limit": 200, "reference_key": None},
        "0 8 * * 0",
    ),
)

# Independent scopes preserve previous deployments and operator-edited schedules.
# No reviewed presentation/media entries exist for Maryah yet, so no empty
# presentation import is advertised as project coverage.
DATASETS += (
    Dataset(
        "maryah-parcels-onwani",
        "property-platform-parcels",
        "Official Al Maryah parcels, with exact acquisition times and quarantine.",
        {"territory": "al-maryah-island"},
        "0 13 * * 0",
    ),
    *(
        Dataset(
            f"maryah-map-{layer}",
            "property-platform-map",
            f"Al Maryah {layer}; preserve source identities and prior observations.",
            {"territory": "al-maryah-island", "layer": layer},
            f"{minute} 14 * * 0",
        )
        for layer, minute in (("district", 0), ("community", 15), ("street", 30), ("osm", 45))
    ),
    Dataset(
        "maryah-osm-bootstrap",
        "property-platform-osm-bootstrap",
        "Manual bounded official OSM acquisition for Al Maryah; original XML retained.",
        {"territory": "al-maryah-island"},
        None,
    ),
    Dataset(
        "maryah-project-references",
        "property-platform-references",
        "Reviewed Al Maryah public sources, without automatic project reconciliation.",
        {"territory": "al-maryah-island", "limit": 200, "reference_key": None},
        "0 15 * * 0",
    ),
    Dataset(
        "maryah-project-details",
        "property-platform-project-details",
        "Refresh reviewed Al Maryah projects independently; retain source history and documents.",
        {"territory": "al-maryah-island"},
        "0 5 * * 6",
    ),
    Dataset(
        "maryah-project-discovery",
        "property-platform-project-discovery",
        "Archive Al Maryah publisher catalogues; discoveries remain review candidates.",
        {"territory": "al-maryah-island"},
        "30 5 * * 6",
    ),
)


DATASETS += tuple(
    Dataset(
        f"{prefix}-parcels-adsdi",
        "property-platform-sdi-parcels",
        "Compare AD-SDI evidence; preserve Onwani geometry and exact capture history.",
        {"territory": territory},
        None,
    )
    for prefix, territory in (
        ("reem", "al-reem-island"),
        ("saadiyat", "saadiyat-island"),
        ("maryah", "al-maryah-island"),
    )
)


# Emirate-wide AD-SDI plots, district by district. Manual: a full municipality is a
# multi-hour acquisition that an operator starts deliberately (F01).
DATASETS += tuple(
    Dataset(
        f"{municipality.lower()}-parcels-adsdi-districts",
        "property-platform-sdi-district-parcels",
        f"AD-SDI plots of {municipality}, district by district; identity checks and quarantine.",
        {"municipality": municipality},
        None,
    )
    for municipality in ("ADM", "AAM", "WRM")
)


def source_registries(territory=DEFAULT_TERRITORY):
    profile = collection_for(territory)
    root = files("property_platform.modules.evidence")
    return (
        json.loads(root.joinpath(profile.reference_registry).read_text(encoding="utf-8")),
        json.loads(root.joinpath(profile.presentation_registry).read_text(encoding="utf-8")),
        json.loads(root.joinpath(profile.media_registry).read_text(encoding="utf-8")),
    )


def reference_identity(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:40]


def execution_identity(run_id: str, operation: str, scope: str) -> str:
    # Same Prefect run/operation/scope always resolves to the same durable DB job.
    return hashlib.sha256(f"ingestion-v1:{run_id}:{operation}:{scope}".encode()).hexdigest()


DATASETS += (
    Dataset(
        "adrec-reem-sales",
        "property-platform-adrec-sales",
        "Complete 90-day public sales snapshot; no invented transaction identity.",
        {"territory": "al-reem-island"},
        "0 9 * * 0",
    ),
    Dataset(
        "adrec-saadiyat-sales",
        "property-platform-adrec-sales",
        "Complete Saadiyat sales snapshot, with original receipts.",
        {"territory": "saadiyat-island"},
        "30 9 * * 0",
    ),
    Dataset(
        "adrec-price-indices",
        "property-platform-adrec-indices",
        "Abu Dhabi city indices; ambiguous source series are quarantined.",
        {"territory": "abu-dhabi"},
        "0 10 * * 0",
    ),
    Dataset(
        "adrec-maryah-sales",
        "property-platform-adrec-sales",
        "Complete Al Maryah sales snapshot; exact public district and retained receipts.",
        {"territory": "al-maryah-island"},
        "45 9 * * 0",
    ),
    Dataset(
        "adrec-abu-dhabi-sales",
        "property-platform-adrec-sales",
        "Complete emirate-wide 90-day sales snapshot; overlaps island-specific snapshots.",
        {"territory": "abu-dhabi"},
        "30 10 * * 0",
    ),
    *(
        Dataset(
            f"abu-dhabi-{dataset}",
            "property-platform-public-context",
            description,
            {"territory": "abu-dhabi", "dataset": dataset},
            f"{minute} 11 * * 0",
        )
        for dataset, minute, description in (
            (
                "health",
                0,
                "DoH public facilities, locations and planned status; not medical advice.",
            ),
            ("schools", 15, "ADEK Charter schools only; ESIS identities, names and locations."),
            (
                "mobility",
                30,
                "Published bus routes and endpoints; no invented stops or travel times.",
            ),
            ("statistics", 45, "SCAD census measures with reference year and disclosure rounding."),
        )
    ),
)
