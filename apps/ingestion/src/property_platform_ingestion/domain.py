"""Sync-only boundary to Django; acquire before opening a canonical write transaction."""

import contextlib
import io
import json
import os
import sys
from pathlib import Path

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
        }
        if not isinstance(request, dict) or set(request) - allowed:
            raise ValueError("Unexpected domain request parameters")
        if request.get("operation") == "check":
            # Introspection performs a read only; migrations are never a startup hook.
            from django.db.migrations.executor import MigrationExecutor

            executor = MigrationExecutor(connections["default"])
            if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                raise SchemaNotReady("Django migrations must be applied before ingestion")
            IngestionExecution.objects.exists()
            rows = orchestration.reference_registry()
            profiles, _ = property_import.registry()
            return {
                "status": "succeeded",
                "summary": {
                    "references": len(rows),
                    "presentations": len(profiles),
                    "territory": orchestration.TERRITORY,
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
        if operation == "osm_bootstrap":
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
        elif operation == "onwani":
            with SourceHTTP(OnwaniCollector.allowed_urls()) as transport:
                replay = precollect_onwani(OnwaniCollector(transport, territory))
            acquisition = replay.onwani
        elif operation == "map":
            layer = request["scope"].split(":")[1]
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
                if identity["operation"] in {"onwani", "map", "osm_bootstrap"}
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
        result = {"status": "failed", "error": type(exc).__name__}
    print(json.dumps(result))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
