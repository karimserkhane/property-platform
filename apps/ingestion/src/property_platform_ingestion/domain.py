"""Sync-only boundary to Django; acquire before opening a canonical write transaction."""

import contextlib
import io
import json
import logging
import os
import sys
from pathlib import Path

from .registry import TERRITORIES
from .runtime import MAX_REQUEST, checked_receipt_path
from .storage import stored_property_receipt


class SchemaNotReady(ValueError):
    """Apply the explicit Django migrations before starting the ingestion runner."""


def execute(request):
    import django

    django.setup()
    from django.db import connections
    from property_platform.modules.evidence import orchestration, property_import
    from property_platform.modules.evidence.models import IngestionExecution

    from .collectors import (
        MapCollector,
        OnwaniCollector,
        ReferenceCollector,
        SourceHTTP,
        collect_property_receipts,
        precollect_map,
        precollect_onwani,
        precollect_reference,
    )
    from .collectors.properties import property_urls

    identity, acquiring, transport = None, False, None
    try:
        allowed = {
            "operation",
            "scope",
            "execution_key",
            "actor",
            "prefect_flow_run_id",
            "reference_key",
            "receipt_name",
            "action",
            "error",
            "archive_key",
        }
        if not isinstance(request, dict) or set(request) - allowed:
            raise ValueError("Unexpected domain request parameters")
        if request.get("operation") == "prepare_catalogue_rebuild":
            from uuid import UUID

            from django.core.management import call_command
            from property_platform.modules.catalog.models import Project

            if set(request) != {"operation", "actor", "prefect_flow_run_id"}:
                raise ValueError("Catalogue initialization requires an explicit Prefect run")
            UUID(str(request["prefect_flow_run_id"]))
            if not isinstance(request["actor"], str) or not request["actor"].strip():
                raise ValueError("Catalogue initialization requires an operator")
            # An explicit bootstrap pipeline, never a web/runner startup hook.
            call_command("migrate", interactive=False, verbosity=0)
            if Project.objects.exists():
                raise ValueError("Catalogue rebuild requires an empty project catalogue")
            return {"status": "succeeded", "summary": {"schema_ready": True, "projects": 0}}
        if "archive_key" in request and request.get("operation") not in {
            "project_details",
            "project_discovery",
        }:
            raise ValueError("Only a reviewed project source can replay this archive")
        if request.get("operation") in {"routing_graph", "walking_areas"}:
            from property_platform.modules.evidence.accessibility import (
                archive_graph,
                archive_walking,
            )

            from .collectors.accessibility import acquire_graph, build_graph, compute_walking

            if set(request) - {"operation", "actor", "prefect_flow_run_id", "scope"} or request.get(
                "scope", "refresh"
            ) not in {"refresh", "archive"}:
                raise ValueError("Map analysis requires an audited Prefect run")
            values = {
                "actor": request["actor"],
                "run_key": f"{request['operation']}:{request['prefect_flow_run_id']}",
            }
            if request["operation"] == "routing_graph":
                return archive_graph(
                    **values,
                    acquire=acquire_graph,
                    build=build_graph,
                    from_history=request.get("scope") == "archive",
                )
            return archive_walking(**values, compute=compute_walking)
        if request.get("operation") == "construction_activity":
            from property_platform.modules.catalog.territories import TERRITORY_BY_ID
            from property_platform.modules.evidence.activity_import import measure_activity

            from .collectors.sentinel_measure import ActivityCollector

            if set(request) != {"operation", "scope", "actor", "prefect_flow_run_id"}:
                raise ValueError("Activity measurement requires an audited Prefect run")
            if request["scope"] != "all" and request["scope"] not in TERRITORY_BY_ID:
                raise ValueError("Unregistered activity territory")
            with ActivityCollector() as collector:
                return measure_activity(
                    actor=request["actor"],
                    run_key=f"construction_activity:{request['prefect_flow_run_id']}",
                    collector=collector,
                    territory=None if request["scope"] == "all" else request["scope"],
                )
        if request.get("operation") == "data_history":
            from property_platform.modules.evidence.history.pipeline_inventory import check_history

            if set(request) != {"operation", "actor", "prefect_flow_run_id"}:
                raise ValueError("History inventory requires a Prefect run and operator")
            return check_history(
                actor=request["actor"], run_key=f"history:{request['prefect_flow_run_id']}"
            )
        if request.get("operation") == "basemap":
            from datetime import timedelta

            from django.db.models import Q
            from django.utils import timezone
            from property_platform.modules.catalog.territories import TERRITORY_BY_ID
            from property_platform.modules.evidence.basemap_archive import (
                archive_pending,
                seed_area,
            )
            from property_platform.modules.evidence.models import BasemapRequest

            from .collectors.basemaps import BasemapCollector

            if set(request) != {"operation", "scope", "actor", "prefect_flow_run_id"}:
                raise ValueError("Basemap archive requires an audited provider scope")
            provider = request["scope"]
            if provider not in {
                "openfreemap",
                "sentinel-worldcover-2020",
                "sentinel-worldcover-2021",
            }:
                raise ValueError("Unregistered basemap provider")
            for territory in TERRITORIES:
                seed_area(provider, TERRITORY_BY_ID[territory].bounds)
            now = timezone.now()
            pending = (
                BasemapRequest.objects.filter(provider=provider)
                .filter(Q(available=False) | Q(last_attempt_at__lt=now - timedelta(days=7)))
                .filter(
                    Q(last_attempt_at__isnull=True)
                    | Q(last_attempt_at__lt=now - timedelta(hours=1))
                )
            )
            if not pending.exists():
                return {"status": "succeeded", "summary": {"saved": 0, "pending": 0}}
            queued = list(
                pending.order_by("available", "last_attempt_at", "created_at", "pk").values_list(
                    "pk", "z", "x", "y"
                )[:5000]
            )
            with BasemapCollector(provider, [row[1:] for row in queued]) as collector:
                result = archive_pending(
                    provider,
                    actor=request["actor"],
                    acquire=collector,
                    run_key=f"tiles:{request['prefect_flow_run_id']}",
                    request_ids=[row[0] for row in queued],
                )
            return {
                "status": "succeeded"
                if result["status"] in {"succeeded", "busy"}
                else "quarantined",
                "summary": result,
            }
        if request.get("operation") == "project_media_files":
            from .media_files import ingest_files

            if set(request) != {"operation", "actor", "prefect_flow_run_id", "receipt_name"}:
                raise ValueError("File intake requires a private manifest and audited actor")
            root = Path(os.environ.get("INGESTION_STORAGE_DIR", ".cache/ingestion"))
            result = ingest_files(root, request["receipt_name"], actor=request["actor"])
            return {"status": "succeeded", "summary": result}
        if request.get("operation") == "media_storage":
            from property_platform.modules.evidence.media_storage import archive_property_media

            if request.get("action") == "reconcile":
                # No long SQL transaction exists to reconcile: each immutable object has its
                # own committed binding. The next run resumes the remaining captures.
                return {"status": "failed", "error": "MediaStorageInterrupted"}
            if set(request) != {"operation", "actor", "prefect_flow_run_id"}:
                raise ValueError("Media storage accepts only an audited private backfill")
            result = archive_property_media(actor=request["actor"])
            return {"status": "succeeded", "summary": result}
        if request.get("operation") == "check":
            # Introspection performs a read only; migrations are never a startup hook.
            from django.db.migrations.executor import MigrationExecutor

            executor = MigrationExecutor(connections["default"])
            if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                raise SchemaNotReady("Django migrations must be applied before ingestion")
            IngestionExecution.objects.exists()
            from property_platform.modules.evidence.project_discovery import catalogue_registry
            from property_platform.modules.evidence.project_protocol import project_registry

            territories = {}
            for territory in TERRITORIES:
                rows = orchestration.reference_registry(territory)
                profiles, _ = property_import.registry(territory)
                territories[territory] = {
                    "references": len(rows),
                    "presentations": len(profiles),
                    "projects": len(project_registry(territory)),
                    "catalogues": len(catalogue_registry(territory)),
                }
            return {
                "status": "succeeded",
                "summary": {
                    **territories[orchestration.TERRITORY],
                    "territory": orchestration.TERRITORY,
                    "territories": territories,
                    "orchestration_schema": "ready",
                },
            }
        identity = {key: request[key] for key in ("operation", "scope", "execution_key", "actor")}
        previous = orchestration.execution_result(**identity)
        if request.get("action") == "reconcile":
            if request.get("error") not in {"DomainTimeout", "InvalidDomainResponse"}:
                raise ValueError("Unknown reconciliation reason")
            settled = orchestration.execution_result(**identity, include_failed=True)
            if settled:
                return settled
            return orchestration.record_acquisition_failure(
                **identity,
                error=request["error"],
                prefect_flow_run_id=request.get("prefect_flow_run_id"),
            )
        if request.get("action") is not None or "error" in request:
            raise ValueError("Unexpected reconciliation parameters")
        if previous:
            return previous
        operation = request["operation"]
        territory = request["scope"].split(":", 1)[0]
        acquisition, receipt, replay = None, None, None
        acquiring = True
        if operation == "public_context":
            from property_platform.modules.evidence.sources import abu_dhabi

            from .collectors.context import precollect_context, replay_school_archive

            if request.get("receipt_name") is not None:
                storage = Path(os.environ.get("INGESTION_STORAGE_DIR", ".cache/ingestion"))
                path = checked_receipt_path(storage, request["receipt_name"])
                if path.stat().st_size > 8 * 1024 * 1024:
                    raise ValueError("School receipt exceeds its budget")
                raw = path.read_bytes()
                if len(raw) > 8 * 1024 * 1024:
                    raise ValueError("School receipt exceeds its budget")
                replay = replay_school_archive(request["scope"], json.loads(raw))
            else:
                with SourceHTTP(abu_dhabi.urls_for(request["scope"])) as transport:
                    replay = precollect_context(transport, request["scope"])
            acquisition = replay.map
        elif operation in {"adrec_sales", "adrec_indices"}:
            from property_platform.modules.evidence.sources import adrec

            from .collectors.adrec import precollect_adrec

            with SourceHTTP([adrec.SALES, *adrec.INDICES.values()]) as transport:
                replay = precollect_adrec(transport, operation, request["scope"])
            acquisition = replay.map
        elif operation == "osm_bootstrap":
            from urllib.parse import urlencode

            from property_platform.modules.evidence import osm_api_protocol as osm_bootstrap

            from .collectors.snapshots import ReplayFetcher, _params

            replay = ReplayFetcher()
            with SourceHTTP([osm_bootstrap.URL]) as transport:
                for params in osm_bootstrap.boxes(territory):

                    def collect(params=params):
                        acquired = transport.fetch(
                            osm_bootstrap.URL + "?" + urlencode(params),
                            allowed_base=osm_bootstrap.URL,
                            max_bytes=osm_bootstrap.MAX_BYTES,
                            read_timeout_seconds=60,
                        )
                        if acquired.http_status != 200:
                            raise ValueError("OSM bootstrap source failed")
                        osm_bootstrap.decode(acquired.payload)
                        return acquired.payload, acquired.capture_receipt()

                    replay._acquire(("map", osm_bootstrap.URL, _params(params)), collect)
            acquisition = replay.map
        elif operation == "sdi_parcels":
            from property_platform.modules.evidence.sdi_protocol import URL

            from .collectors.sdi import precollect_sdi

            with SourceHTTP([URL, URL + "/query"]) as transport:
                replay = precollect_sdi(transport, territory)
            acquisition = replay.map
        elif operation == "onwani":
            with SourceHTTP(OnwaniCollector.allowed_urls()) as transport:
                replay = precollect_onwani(OnwaniCollector(transport, territory))
            acquisition = replay.onwani
        elif operation == "map":
            layer = request["scope"].split(":")[1]
            if layer == "overture":
                from property_platform.modules.evidence.overture_places import URL

                from .collectors.overture import acquire_places
                from .collectors.snapshots import ReplayFetcher, _params

                replay = ReplayFetcher()
                replay._acquire(("map", URL, _params({})), lambda: acquire_places(territory))
            else:
                with SourceHTTP(MapCollector.allowed_urls()) as transport:
                    replay = precollect_map(MapCollector(transport, territory), layer)
            acquisition = replay.map
        elif operation == "references":
            rows = orchestration.reference_registry(territory)
            key = request["reference_key"]
            row = next(row for row in rows if orchestration.reference_identity(row["url"]) == key)
            with SourceHTTP([row["url"]]) as transport:
                replay = precollect_reference(ReferenceCollector(transport, rows), row["url"])
            acquisition = replay.reference
        elif operation == "property_presentations":
            profiles, photos = property_import.registry(territory)

            def collect():
                with SourceHTTP(property_urls(profiles, photos)) as transport:
                    return collect_property_receipts(transport, profiles, photos)

            receipt = stored_property_receipt(
                Path(os.environ.get("INGESTION_STORAGE_DIR", ".cache/ingestion")),
                request["execution_key"],
                collect,
            )
        elif operation == "project_discovery":
            from property_platform.modules.evidence.project_discovery import (
                candidates_for,
                catalogue_byte_limit,
                catalogue_for,
            )

            from .project_archive import archive_catalogue_batch, read_catalogue_batch

            definition = catalogue_for(request["scope"])

            def collect_catalogue():
                nonlocal transport
                with SourceHTTP([definition["url"]]) as transport:
                    item = transport.fetch(
                        definition["url"], max_bytes=catalogue_byte_limit(definition)
                    )
                    candidates_for(definition, item.payload)
                    return [item.property_receipt()]

            storage = Path(os.environ.get("INGESTION_STORAGE_DIR", ".cache/ingestion"))
            if request.get("archive_key") is not None:
                receipt = read_catalogue_batch(storage, request["scope"], request["archive_key"])
            else:
                receipt = stored_property_receipt(
                    storage, request["execution_key"], collect_catalogue
                )
                archive_catalogue_batch(storage, request["scope"], receipt)
        elif operation == "project_details":
            from property_platform.modules.evidence.project_protocol import (
                project_registry,
                project_urls,
            )

            from .collectors.projects import collect_project_receipts
            from .project_archive import archive_project_batch, read_project_batch

            projects = project_registry(request["scope"])

            def collect_projects():
                nonlocal transport
                with SourceHTTP(project_urls(projects)) as transport:
                    return collect_project_receipts(transport, projects)

            storage = Path(os.environ.get("INGESTION_STORAGE_DIR", ".cache/ingestion"))
            if request.get("archive_key") is not None:
                receipt = read_project_batch(storage, request["scope"], request["archive_key"])
            else:
                receipt = stored_property_receipt(
                    storage, request["execution_key"], collect_projects
                )
                if len(request["scope"].split(":")) == 3:
                    archive_project_batch(storage, request["scope"], receipt)
        elif operation == "imagery":
            storage = Path(os.environ.get("INGESTION_STORAGE_DIR", ".cache/ingestion"))
            path = checked_receipt_path(storage, request["receipt_name"])
            if path.stat().st_size > 16 * 1024 * 1024:
                raise ValueError("Imagery receipt exceeds its budget")
            with path.open("rb") as handle:
                content = handle.read(16 * 1024 * 1024 + 1)
            if len(content) > 16 * 1024 * 1024:
                raise ValueError("Imagery receipt exceeds its budget")
            receipt = json.loads(content.decode("utf-8-sig"))
        acquiring = False
        result = orchestration.execute_import(
            **identity,
            acquisition=acquisition,
            receipt=receipt,
            reference_key=request.get("reference_key"),
            prefect_flow_run_id=request.get("prefect_flow_run_id"),
            completion_check=replay.assert_consumed if replay else None,
        )
        return result
    except Exception as exc:
        if acquiring and identity is not None:
            received = (
                [
                    {"payload": item.payload, "receipt": item.capture_receipt()}
                    for item in transport.acquisitions
                ]
                if identity["operation"]
                in {
                    "sdi_parcels",
                    "onwani",
                    "map",
                    "osm_bootstrap",
                    "adrec_sales",
                    "adrec_indices",
                    "public_context",
                    "project_details",
                    "project_discovery",
                }
                and transport is not None
                else None
            )
            return orchestration.record_acquisition_failure(
                **identity,
                error=exc,
                prefect_flow_run_id=request.get("prefect_flow_run_id"),
                received_acquisitions=received,
            )
        raise
    finally:
        connections.close_all()


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST + 1)
        if len(raw) > MAX_REQUEST:
            raise ValueError("Domain request exceeds its budget")
        # Legacy command diagnostics must never corrupt the JSON protocol.
        with contextlib.redirect_stdout(io.StringIO()):
            result = execute(json.loads(raw))
    except Exception as exc:
        # The traceback goes to stderr (operator logs); the flow result keeps the class only.
        logging.getLogger(__name__).error("Domain request failed", exc_info=exc)
        result = {"status": "failed", "error": type(exc).__name__}
    print(json.dumps(result))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
