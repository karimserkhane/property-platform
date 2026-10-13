"""Explicit deployed datasets. Registering a territory never invents its data."""

import hashlib
import json
from dataclasses import dataclass
from importlib.resources import files

TERRITORY = "al-reem-island"
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
)


def source_registries():
    root = files("property_platform.modules.evidence")
    return (
        json.loads(root.joinpath("project_sources.json").read_text(encoding="utf-8")),
        json.loads(root.joinpath("property_presentations.json").read_text(encoding="utf-8")),
        json.loads(root.joinpath("property_media.json").read_text(encoding="utf-8")),
    )


def reference_identity(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:40]


def execution_identity(run_id: str, operation: str, scope: str) -> str:
    # Same Prefect run/operation/scope always resolves to the same durable DB job.
    return hashlib.sha256(f"ingestion-v1:{run_id}:{operation}:{scope}".encode()).hexdigest()
