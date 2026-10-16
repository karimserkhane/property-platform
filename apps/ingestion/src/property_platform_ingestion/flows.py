"""One deployed dataset at a time; persistence belongs to Django's audited gateway."""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

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
        raise ValueError("Operator must contain 1â€“80 characters")
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
        logger.warning(
            "Valid observations were applied; ambiguous or rejected data remain in quarantine."
        )
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
        raise ValueError("Reference limit must be 1â€“200")
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
    result = ingest_source("property_presentations", territory, actor)
    result["media_storage"] = archive_media(actor)
    return result


@flow(name="property-platform-project-details", retries=0)
def project_details(
    territory: Literal["al-reem-island", "saadiyat-island"] = TERRITORY, actor: str = "manual"
):
    """Reviewed factual project observations; promoter media remain external references."""
    from property_platform.modules.evidence.project_protocol import project_registry

    results, failures = [], []
    for project in project_registry(territory):
        scope = f"{territory}:{project['slug']}"
        try:
            results.append(
                ingest_source.with_options(name=f"Project: {project['name']}")(
                    "project_details", scope, actor
                )
            )
        except IngestionFailure as exc:
            get_run_logger().warning(
                "Project %s failed: %s",
                project["slug"],
                exc.result.get("error", "SourceUnavailable"),
            )
            failures.append(project["slug"])
    if failures:
        raise IngestionFailure(
            {
                "status": "failed",
                "error": "IncompleteProjectBatch",
                "summary": {"succeeded": len(results), "failed": failures},
            }
        )
    return results


@flow(name="property-platform-project-discovery", retries=0)
def project_discovery(
    territory: Literal["al-reem-island", "saadiyat-island"] = TERRITORY, actor: str = "manual"
):
    from property_platform.modules.evidence.project_discovery import catalogue_registry

    results, failures = [], []
    for catalogue in catalogue_registry(territory):
        scope = f"{territory}:{catalogue['key']}"
        try:
            results.append(
                ingest_source.with_options(name=f"Catalogue: {catalogue['publisher_key']}")(
                    "project_discovery", scope, actor
                )
            )
        except IngestionFailure:
            failures.append(catalogue["key"])
    if failures:
        raise IngestionFailure(
            {
                "status": "failed",
                "error": "IncompleteCatalogueBatch",
                "summary": {"succeeded": len(results), "failed": failures},
            }
        )
    return results


@task(name="Archive acquired media", retries=0, cache_policy=NO_CACHE)
def archive_media(actor: str) -> dict:
    run_id = flow_run.id
    if run_id is None or not isinstance(actor, str) or not 1 <= len(actor.strip()) <= 80:
        raise ValueError("An active Prefect run and a 1â€“80 character operator are required")
    result = invoke_domain(
        {
            "operation": "media_storage",
            "actor": f"Prefect/{run_id}/{actor.strip()}",
            "prefect_flow_run_id": run_id,
        }
    )
    get_run_logger().info("Private media archival: %s", result["summary"])
    return result


@flow(name="property-platform-media-storage", retries=0)
def media_storage(actor: str = "manual"):
    """Resume a bounded private backfill; public CDN publication stays an explicit command."""
    return archive_media(actor)


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


@flow(name="property-platform-adrec-sales", retries=0)
def adrec_sales(
    territory: Literal["al-reem-island", "saadiyat-island", "abu-dhabi"] = TERRITORY,
    actor: str = "scheduled",
):
    """Snapshot 90 completed Dubai days. Scheduled run time fixes the retry scope."""
    from property_platform.modules.evidence.adrec import sales_scope

    scheduled = flow_run.scheduled_start_time
    if isinstance(scheduled, str):
        scheduled = datetime.fromisoformat(scheduled)
    as_of = scheduled.astimezone(ZoneInfo("Asia/Dubai")).date()
    return ingest_source("adrec_sales", sales_scope(territory, as_of=as_of), actor)


@flow(name="property-platform-adrec-indices", retries=0)
def adrec_indices(territory: Literal["abu-dhabi"] = "abu-dhabi", actor: str = "scheduled"):
    """Capture sale/rent series; indistinguishable conflicting series stay unusable."""
    return ingest_source("adrec_indices", territory, actor)


@flow(name="property-platform-public-context", retries=0)
def public_context(
    dataset: Literal["health", "schools", "mobility", "statistics", "districts"] = "health",
    territory: Literal["abu-dhabi"] = "abu-dhabi",
    actor: str = "scheduled",
    receipt_name: str | None = None,
):
    """Complete authority snapshot, without name-only property reconciliation."""
    if receipt_name is not None:
        if dataset != "schools":
            raise ValueError("Manual archives are only registered for ADEK schools")
        return ingest_source(
            "public_context", f"{territory}:{dataset}", actor, receipt_name=receipt_name
        )
    return ingest_source("public_context", f"{territory}:{dataset}", actor)


@flow(name="property-platform-project-media-files", retries=0)
def project_media_files(receipt_name: str = "project-media.json", actor: str = "manual"):
    """Idempotent private operator files, without approval or public publication."""
    run_id = flow_run.id
    if run_id is None or not isinstance(actor, str) or not 1 <= len(actor.strip()) <= 80:
        raise ValueError("An active Prefect run and a 1â€“80 character operator are required")
    return invoke_domain(
        {
            "operation": "project_media_files",
            "receipt_name": receipt_name,
            "actor": f"Prefect/{run_id}/{actor.strip()}",
            "prefect_flow_run_id": run_id,
        }
    )


FLOWS = {
    f.name: f
    for f in (
        parcels,
        map_layer,
        references,
        presentations,
        project_details,
        project_discovery,
        imagery,
        readiness,
        osm_bootstrap,
        adrec_sales,
        adrec_indices,
        public_context,
        media_storage,
        project_media_files,
    )
}
