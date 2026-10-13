"""One deployed dataset at a time; persistence belongs to Django's audited gateway."""

from typing import Literal

from prefect import flow, get_run_logger, task
from prefect.cache_policies import NO_CACHE
from prefect.runtime import flow_run

from .registry import TERRITORY, execution_identity, reference_identity, source_registries
from .runtime import IngestionFailure, invoke_domain


@task(name="Acquire and ingest source", retries=0, cache_policy=NO_CACHE)
def ingest_source(operation: str, scope: str, actor: str, **parameters) -> dict:
    run_id = flow_run.id
    if run_id is None:
        raise ValueError("An active Prefect flow run is required")
    if not isinstance(actor, str) or not 1 <= len(actor.strip()) <= 80:
        raise ValueError("Operator must contain 1–80 characters")
    result = invoke_domain(
        {
            "operation": operation,
            "scope": scope,
            "execution_key": execution_identity(run_id, operation, scope),
            "prefect_flow_run_id": run_id,
            "actor": f"Prefect/{run_id}/{actor.strip()}",
            **parameters,
        }
    )
    logger = get_run_logger()
    logger.info(
        "%s %s: %s; execution=%s reused=%s summary=%s",
        operation,
        scope,
        result["status"],
        result.get("execution_id"),
        result.get("reused"),
        result.get("summary"),
    )
    if result["status"] == "quarantined":
        logger.warning("Valid records were applied; rejected geometries remain in quarantine.")
    return result


@flow(name="property-platform-parcels", retries=0)
def parcels(
    territory: Literal["al-reem-island", "saadiyat-island"] = TERRITORY, actor: str = "scheduled"
):
    """Refresh official parcels while retaining original captures and quarantine."""
    return ingest_source("onwani", territory, actor)


@flow(name="property-platform-map", retries=0)
def map_layer(
    layer: Literal["district", "community", "street", "osm"] = "osm",
    territory: Literal["al-reem-island", "saadiyat-island"] = TERRITORY,
    actor: str = "scheduled",
):
    """Refresh one source layer; buildings/places share the OSM acquisition."""
    return ingest_source("map", f"{territory}:{layer}", actor)


@flow(name="property-platform-references", retries=0)
def references(
    limit: int = 200,
    reference_key: str | None = None,
    territory: Literal["al-reem-island", "saadiyat-island"] = TERRITORY,
    actor: str = "scheduled",
):
    """Collect reviewed references independently; one source failure does not skip others."""
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("Reference limit must be 1–200")
    rows, _, _ = source_registries(territory)
    if reference_key is not None:
        rows = [row for row in rows if reference_identity(row["url"]) == reference_key]
        if len(rows) != 1:
            raise ValueError("Unknown reference identity")
    results, failures = [], []
    for row in rows[:limit]:
        key = reference_identity(row["url"])
        try:
            result = ingest_source.with_options(name=f"Reference: {row['label'][:80]}")(
                "references",
                f"{territory}:{key}",
                actor,
                reference_key=key,
            )
            results.append(result)
        except IngestionFailure as exc:
            failures.append(exc.result)
    get_run_logger().info("References: %s succeeded; %s failed", len(results), len(failures))
    if failures:
        raise IngestionFailure(
            {
                "status": "failed",
                "error": "IncompleteReferenceBatch",
                "summary": {"succeeded": len(results), "failed": len(failures)},
            }
        )
    return results


@flow(name="property-platform-presentations", retries=0)
def presentations(
    territory: Literal["al-reem-island", "saadiyat-island"] = TERRITORY, actor: str = "scheduled"
):
    """Refresh the reviewed property profiles and licensed media as one validated batch."""
    return ingest_source("property_presentations", territory, actor)


@flow(name="property-platform-imagery", retries=0)
def imagery(
    receipt_name: str = "sentinel-reem.json",
    territory: Literal["al-reem-island", "saadiyat-island"] = TERRITORY,
    actor: str = "manual",
):
    """Import an existing isolated-raster receipt; no recurring historical scene downloads."""
    return ingest_source("imagery", territory, actor, receipt_name=receipt_name)


@flow(name="property-platform-readiness", retries=0)
def readiness():
    """Check schema and reviewed registries without a network acquisition or DB mutation."""
    result = invoke_domain({"operation": "check"})
    get_run_logger().info("Ingestion readiness: %s", result["summary"])
    return result


@flow(name="property-platform-osm-bootstrap", retries=0)
def osm_bootstrap(territory: Literal["saadiyat-island"] = "saadiyat-island", actor: str = "manual"):
    """One-off bounded API windows, never scheduled bulk harvesting."""
    return ingest_source("osm_bootstrap", territory, actor)


FLOWS = {
    f.name: f
    for f in (parcels, map_layer, references, presentations, imagery, readiness, osm_bootstrap)
}
