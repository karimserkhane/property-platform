"""One deployed dataset at a time; persistence belongs to Django's audited gateway."""

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from prefect import flow, get_run_logger, task
from prefect.cache_policies import NO_CACHE
from prefect.runtime import flow_run
from property_platform.modules.evidence.source_rights import collection_allowed

from .registry import (
    TERRITORY,
    Territory,
    execution_identity,
    reference_identity,
    source_registries,
)
from .runtime import SDI_TIMEOUT, TIMEOUT, IngestionFailure, invoke_domain


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
            "execution_key": execution_identity(
                run_id,
                operation,
                scope + ":archive:" + parameters["archive_key"]
                if parameters.get("archive_key")
                else scope,
            ),
            "prefect_flow_run_id": run_id,
            "actor": f"Prefect/{run_id}/{actor.strip()}",
            **parameters,
        },
        timeout=SDI_TIMEOUT if operation == "sdi_parcels" else TIMEOUT,
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
def parcels(territory: Territory = TERRITORY, actor: str = "scheduled"):
    """Refresh official parcels while retaining original captures and quarantine."""
    return ingest_source("onwani", territory, actor)


@flow(name="property-platform-sdi-parcels", retries=0)
def sdi_parcels(territory: Territory = TERRITORY, actor: str = "scheduled"):
    """Compare official plot identities and preserve conflicting geometries without replacement."""
    return ingest_source("sdi_parcels", territory, actor)


@flow(name="property-platform-sdi-district-parcels", retries=0)
def sdi_district_parcels(
    municipality: Literal["ADM", "AAM", "WRM"] = "ADM",
    districts: list[str] | None = None,
    actor: str = "manual",
):
    """Import reviewed AD-SDI districts one audited run each; a failure never hides others."""
    from property_platform.modules.evidence.maps import sdi_protocol

    registered = sdi_protocol.scopes_in(municipality)
    scopes = registered if districts is None else list(dict.fromkeys(districts))
    if not scopes or any(scope not in registered for scope in scopes):
        raise ValueError("Districts must be reviewed AD-SDI scopes of this municipality")
    results, failed = {}, []
    for scope in scopes:
        try:
            results[scope] = ingest_source("sdi_parcels", scope, actor)
        except IngestionFailure as exc:
            results[scope] = exc.result
            failed.append(scope)
    if failed:
        raise IngestionFailure(
            {"status": "failed", "error": "DistrictImportFailed", "failed_scopes": failed}
        )
    return results


@flow(name="property-platform-map", retries=0)
def map_layer(
    layer: Literal["district", "community", "street", "osm", "overture"] = "osm",
    territory: Territory = TERRITORY,
    actor: str = "scheduled",
):
    """Refresh one source layer; buildings/places share the OSM acquisition."""
    return ingest_source("map", f"{territory}:{layer}", actor)


@flow(name="property-platform-references", retries=0)
def references(
    limit: int = 200,
    reference_key: str | None = None,
    territory: Territory = TERRITORY,
    actor: str = "scheduled",
):
    """Collect reviewed references independently; one source failure does not skip others."""
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("Reference limit must be 1â€“200")
    rows, _, _ = source_registries(territory)
    # A site whose terms forbid collection stays registered for replays only (A19).
    rows = [row for row in rows if collection_allowed(row["url"])]
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
def presentations(territory: Territory = TERRITORY, actor: str = "scheduled"):
    """Refresh the reviewed property profiles and licensed media as one validated batch."""
    result = ingest_source("property_presentations", territory, actor)
    result["media_storage"] = archive_media(actor)
    return result


@flow(name="property-platform-project-details", retries=0)
def project_details(
    territory: Territory = TERRITORY,
    actor: str = "manual",
    project_slug: str | None = None,
    source_kind: Literal["all", "developer", "publisher", "broker", "authority"] = "all",
    acquisition_mode: Literal["live", "archive_latest", "archive_all"] = "live",
):
    """Reviewed factual project observations; promoter media remain external references."""
    from property_platform.modules.evidence.projects.project_protocol import project_registry

    from .project_archive import project_batches

    if acquisition_mode not in {"live", "archive_latest", "archive_all"}:
        raise ValueError("Unknown project acquisition mode")

    results, failures = [], []
    scope = f"{territory}:{project_slug}" if project_slug is not None else territory
    sources = [
        (project, source)
        for project in project_registry(scope)
        for source in project["sources"]
        if source["role"] != "terms"
        and collection_allowed(source["url"])
        and (source_kind == "all" or source.get("source_kind", "developer") == source_kind)
    ]
    for project, source in sources:
        source_key = hashlib.sha256(source["url"].encode()).hexdigest()
        scope = f"{territory}:{project['slug']}:{source_key}"
        try:
            if acquisition_mode == "live":
                versions = (None,)
            else:
                root = Path(os.environ.get("INGESTION_STORAGE_DIR", ".cache/ingestion"))
                versions = project_batches(root, scope)
                if not versions:
                    raise ValueError("No preserved receipts for this reviewed project source")
                if acquisition_mode == "archive_latest":
                    versions = versions[-1:]
            for key in versions:
                results.append(
                    ingest_source.with_options(
                        name=f"Project: {project['name']} ({source['parser']}; {acquisition_mode})"
                    )("project_details", scope, actor, **({"archive_key": key} if key else {}))
                )
        except (IngestionFailure, ValueError, OSError) as exc:
            get_run_logger().warning(
                "Project %s failed: %s",
                project["slug"],
                exc.result.get("error", "SourceUnavailable")
                if isinstance(exc, IngestionFailure)
                else type(exc).__name__,
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
def project_discovery(territory: Territory = TERRITORY, actor: str = "manual"):
    from property_platform.modules.evidence.projects.project_discovery import catalogue_registry

    results, failures = [], []
    for catalogue in catalogue_registry(territory):
        if not collection_allowed(catalogue["url"]):
            continue
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
    territory: Literal["al-reem-island"] = TERRITORY,
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
def osm_bootstrap(
    territory: Territory = "saadiyat-island",
    actor: str = "manual",
):
    """One-off bounded API windows, never scheduled bulk harvesting."""
    return ingest_source("osm_bootstrap", territory, actor)


@flow(name="property-platform-adrec-sales", retries=0)
def adrec_sales(
    territory: Literal[
        "al-reem-island", "saadiyat-island", "al-maryah-island", "abu-dhabi"
    ] = TERRITORY,
    actor: str = "scheduled",
):
    """Snapshot 90 completed Dubai days. Scheduled run time fixes the retry scope."""
    from property_platform.modules.evidence.sources.adrec import sales_scope

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


@flow(name="property-platform-source-rights", retries=0)
def source_rights(actor: str = "scheduled"):
    """Mirror the reviewed source rights into the database; no source is contacted."""
    run_id = flow_run.id
    if run_id is None or not 1 <= len(actor.strip()) <= 80:
        raise ValueError("An active Prefect run and operator are required")
    result = invoke_domain(
        {
            "operation": "source_rights",
            "actor": f"Prefect/{run_id}/{actor.strip()}",
            "prefect_flow_run_id": run_id,
        }
    )
    if result["status"] == "failed":
        raise IngestionFailure(result)
    return result


@flow(name="property-platform-data-history", retries=0)
def data_history(actor: str = "scheduled"):
    run_id = flow_run.id
    if run_id is None or not 1 <= len(actor.strip()) <= 80:
        raise ValueError("An active Prefect run and operator are required")
    result = invoke_domain(
        {
            "operation": "data_history",
            "actor": f"Prefect/{run_id}/{actor.strip()}",
            "prefect_flow_run_id": run_id,
        }
    )
    if result["status"] == "failed":
        raise IngestionFailure(result)
    return result


@flow(name="property-platform-basemap-archive", retries=0)
def basemap_archive(
    provider: Literal[
        "openfreemap", "sentinel-worldcover-2020", "sentinel-worldcover-2021"
    ] = "openfreemap",
    actor: str = "scheduled",
):
    run_id = flow_run.id
    if run_id is None or not 1 <= len(actor.strip()) <= 80:
        raise ValueError("An active Prefect run and operator are required")
    return invoke_domain(
        {
            "operation": "basemap",
            "scope": provider,
            "actor": f"Prefect/{run_id}/{actor.strip()}",
            "prefect_flow_run_id": run_id,
        }
    )


@flow(name="property-platform-routing-graph", retries=0)
def routing_graph(actor: str = "scheduled", refresh: bool = True):
    """Archive the reviewed OSM extract, then prepare a versioned local graph."""
    run_id = flow_run.id
    if run_id is None or not 1 <= len(actor.strip()) <= 80:
        raise ValueError("An active Prefect run and operator are required")
    result = invoke_domain(
        {
            "operation": "routing_graph",
            "scope": "refresh" if refresh else "archive",
            "actor": f"Prefect/{run_id}/{actor.strip()}",
            "prefect_flow_run_id": run_id,
        },
        timeout=1200,
    )
    if result["status"] == "failed":
        raise IngestionFailure(result)
    return result


@flow(name="property-platform-construction-activity", retries=0)
def construction_activity(territory: str = "all", actor: str = "scheduled"):
    """Measure ground change of reviewed project parcels on recent Sentinel-2 scenes."""
    run_id = flow_run.id
    if run_id is None or not 1 <= len(actor.strip()) <= 80:
        raise ValueError("An active Prefect run and operator are required")
    result = invoke_domain(
        {
            "operation": "construction_activity",
            "scope": territory,
            "actor": f"Prefect/{run_id}/{actor.strip()}",
            "prefect_flow_run_id": run_id,
        },
        timeout=1200,
    )
    if result["status"] == "failed":
        raise IngestionFailure(result)
    return result


@flow(name="property-platform-walking-areas", retries=0)
def walking_areas(actor: str = "scheduled"):
    """Compute queued 5/10/15-minute walking areas from the archived graph."""
    run_id = flow_run.id
    if run_id is None or not 1 <= len(actor.strip()) <= 80:
        raise ValueError("An active Prefect run and operator are required")
    return invoke_domain(
        {
            "operation": "walking_areas",
            "actor": f"Prefect/{run_id}/{actor.strip()}",
            "prefect_flow_run_id": run_id,
        }
    )


@flow(name="property-platform-backup", retries=0)
def backup(actor: str = "scheduled"):
    """Dump the database from one snapshot, mirror private files, then apply retention."""
    from . import backups

    result = backups.create_backup()
    result["pruned"] = backups.prune()
    get_run_logger().info("Backup %s by %s: %s", result["name"], actor, result)
    return result


@flow(name="property-platform-restore-check", retries=0)
def restore_check(actor: str = "scheduled"):
    """Restore the newest dump into a throwaway database and compare row counts."""
    from . import backups

    result = backups.restore_check()
    get_run_logger().info("Restore check by %s: %s", actor, result)
    if not result["ok"]:
        raise IngestionFailure({"status": "failed", "error": "RestoreMismatch", **result})
    return result


@flow(name="property-platform-rebuild-check", retries=0)
def rebuild_check(actor: str = "manual-check"):
    """Replay archived captures in a fresh database; fail on incomplete reconstruction."""
    from . import rebuilds

    if flow_run.id is None:
        raise ValueError("An active Prefect run is required")
    result = rebuilds.rebuild_check(actor=actor, run_id=str(flow_run.id))
    get_run_logger().info("Source rebuild check: %s", result)
    if not result["ok"]:
        raise IngestionFailure({"status": "failed", "error": "IncompleteSourceRebuild", **result})
    return result


from .project_bootstrap import rebuild_projects  # noqa: E402

FLOWS = {
    f.name: f
    for f in (
        parcels,
        sdi_parcels,
        sdi_district_parcels,
        map_layer,
        references,
        presentations,
        project_details,
        project_discovery,
        rebuild_projects,
        imagery,
        readiness,
        osm_bootstrap,
        adrec_sales,
        adrec_indices,
        public_context,
        media_storage,
        project_media_files,
        basemap_archive,
        source_rights,
        data_history,
        routing_graph,
        walking_areas,
        construction_activity,
        backup,
        restore_check,
        rebuild_check,
    )
}
