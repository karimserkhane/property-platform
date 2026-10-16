"""Explicit deployed datasets. Registering a territory never invents its data."""

import hashlib
import json
from dataclasses import dataclass
from importlib.resources import files

from property_platform.modules.evidence.collection_profiles import DEFAULT_TERRITORY, collection_for

TERRITORY = DEFAULT_TERRITORY
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


# Same reviewed connectors, distinct source identities and deployment scopes.
DATASETS += (
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
