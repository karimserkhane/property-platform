"""Explicit rebuild of an empty project catalogue through ordinary audited imports."""

import os
from pathlib import Path
from typing import Literal

from prefect import flow, get_run_logger, task
from prefect.cache_policies import NO_CACHE
from prefect.runtime import flow_run
from property_platform.modules.evidence.projects.project_protocol import project_registry
from property_platform.modules.evidence.source_rights import collection_allowed

from .project_archive import (
    catalogue_batches,
    index_project_checkpoints,
    project_batches,
    project_source_scope,
)
from .registry import TERRITORIES, Territory
from .runtime import IngestionFailure, invoke_domain


@task(name="Initialize empty catalogue schema", retries=0, cache_policy=NO_CACHE)
def prepare_catalogue(actor):
    if flow_run.id is None or not isinstance(actor, str) or not 1 <= len(actor.strip()) <= 80:
        raise ValueError("An active Prefect run and operator are required")
    return invoke_domain(
        {
            "operation": "prepare_catalogue_rebuild",
            "actor": f"Prefect/{flow_run.id}/{actor.strip()}",
            "prefect_flow_run_id": flow_run.id,
        }
    )


@task(name="Index preserved project source receipts", retries=0, cache_policy=NO_CACHE)
def index_project_archive():
    return index_project_checkpoints(
        Path(os.environ.get("INGESTION_STORAGE_DIR", ".cache/ingestion"))
    )


@flow(name="property-platform-project-rebuild", retries=0)
def rebuild_projects(
    actor: str = "manual-rebuild",
    mode: Literal["archive", "archive_or_live", "live"] = "archive",
    include_geography: bool = False,
    include_catalogues: bool = True,
    territory: Territory | None = None,
):
    """Target DATABASE_URL must have no projects. No tables or records are deleted.

    Archive mode replays all preserved source versions, retaining original clocks.
    Optional geography uses the ordinary registered collectors before identity
    reconciliation; it needs their public sources and is reported separately.
    """
    from .flows import ingest_source, map_layer, parcels, references, sdi_parcels

    if mode not in {"archive", "archive_or_live", "live"}:
        raise ValueError("Unknown catalogue rebuild mode")
    prepare_catalogue(actor)
    indexed = index_project_archive()
    successes, failures, geography, forbidden = [], [], [], []
    if include_geography:
        for area in (territory,) if territory else TERRITORIES:
            for label, collect in (
                ("parcels", lambda area=area: parcels(territory=area, actor=actor)),
                ("parcels-adsdi", lambda area=area: sdi_parcels(territory=area, actor=actor)),
                *(
                    (
                        layer,
                        lambda area=area, layer=layer: map_layer(
                            layer=layer, territory=area, actor=actor
                        ),
                    )
                    for layer in ("district", "community", "street", "osm")
                ),
                (
                    "references",
                    lambda area=area: references(territory=area, actor=actor),
                ),
            ):
                try:
                    collect()
                    geography.append(f"{area}:{label}")
                except IngestionFailure:
                    failures.append(f"{area}:{label}")
    root = Path(os.environ.get("INGESTION_STORAGE_DIR", ".cache/ingestion"))
    for project in project_registry(territory):
        for source in project["sources"]:
            if source["role"] == "terms":
                continue
            scope = project_source_scope(project, source)
            try:
                versions = () if mode == "live" else project_batches(root, scope)
                if versions:
                    for key in versions:
                        ingest_source.with_options(name=f"Replay: {project['name']} {key[:12]}")(
                            "project_details", scope, actor, archive_key=key
                        )
                    successes.append({"scope": scope, "versions": len(versions), "mode": "archive"})
                elif not collection_allowed(source["url"]):
                    # Its preserved history replays above; its terms forbid collection (A19).
                    forbidden.append(scope)
                elif mode == "archive":
                    failures.append(scope)
                else:
                    ingest_source("project_details", scope, actor)
                    successes.append({"scope": scope, "versions": 1, "mode": "live"})
            except IngestionFailure, ValueError, OSError:
                failures.append(scope)
    catalogue_versions = 0
    if include_catalogues:
        from property_platform.modules.evidence.projects.project_discovery import catalogue_registry

        for definition in catalogue_registry(territory):
            scope = f"{definition['territory_scope']}:{definition['key']}"
            try:
                versions = () if mode == "live" else catalogue_batches(root, scope)
                if versions:
                    for key in versions:
                        ingest_source.with_options(name=f"Replay catalogue: {definition['key']}")(
                            "project_discovery", scope, actor, archive_key=key
                        )
                        catalogue_versions += 1
                elif not collection_allowed(definition["url"]):
                    forbidden.append(scope)
                elif mode == "archive":
                    failures.append(scope)
                else:
                    ingest_source("project_discovery", scope, actor)
                    catalogue_versions += 1
            except IngestionFailure, ValueError, OSError:
                failures.append(scope)
    summary = {
        "sources": len(successes),
        "source_versions": sum(row["versions"] for row in successes),
        "catalogue_versions": catalogue_versions,
        "geography_layers": geography,
        "missing_or_failed": failures,
        "forbidden_without_archive": forbidden,
        "archive_index": indexed,
    }
    get_run_logger().info("Catalogue rebuild: %s", summary)
    if failures:
        raise IngestionFailure(
            {"status": "failed", "error": "IncompleteCatalogueRebuild", "summary": summary}
        )
    return summary
