"""Durable execution gateway. Prefect owns scheduling; evidence owns canonical writes.

Transport is injected and may replay captures collected before entering this transaction.
An execution's terminal marker commits with its catalogue writes. Never run this module
inside an asyncio event-loop thread or behind a PostgreSQL transaction pooler.
"""

import hashlib
import json
import re
import uuid

from django.db import connection, transaction
from django.db.models import F
from django.utils import timezone

from . import imagery_import, map_import, osm_bootstrap, property_import, research_import, services
from .collection_profiles import DEFAULT_TERRITORY, collection_for
from .failed_acquisitions import source_definition, validate_received_acquisitions
from .models import Capture, IngestionExecution, IngestionRun, Source

OPERATIONS = {"onwani", "map", "references", "property_presentations", "imagery", "osm_bootstrap"}
TERMINAL = {"succeeded", "quarantined"}
TERRITORY = DEFAULT_TERRITORY


class ImportBusy(RuntimeError):
    """Another importer holds the shared source lock; no attempt was consumed."""


def reference_registry(territory=DEFAULT_TERRITORY):
    """Only reviewed registry entries can be selected, never user supplied URLs."""
    path = research_import.REGISTRY.with_name(collection_for(territory).reference_registry)
    return json.loads(path.read_text(encoding="utf-8"))


def reference_identity(url):
    return hashlib.sha256(url.encode()).hexdigest()[:40]


def _validate_identity(operation, scope, execution_key, actor, reference_key=None):
    if operation not in OPERATIONS or not re.fullmatch(r"[0-9a-f]{64}", execution_key):
        raise ValueError("Invalid ingestion operation or execution identity")
    if not isinstance(actor, str) or not 1 <= len(actor.strip()) <= 160:
        raise ValueError("Valid actor required")
    territory = scope.split(":", 1)[0]
    collection_for(territory)
    if territory != DEFAULT_TERRITORY and operation == "imagery":
        raise ValueError("No reviewed imagery registered for this territory")
    if operation == "osm_bootstrap":
        osm_bootstrap.boxes(territory)
    expected_scope = territory
    reference = None
    if operation == "map":
        if scope not in {f"{territory}:{layer}" for layer in (*map_import.protocol.LAYERS, "osm")}:
            raise ValueError("Unknown map ingestion scope")
        expected_scope = scope
    elif operation == "references":
        if reference_key is None:
            reference_key = scope.removeprefix(territory + ":")
        reference = next(
            (
                row
                for row in reference_registry(territory)
                if reference_identity(row["url"]) == reference_key
            ),
            None,
        )
        if reference is None:
            raise ValueError("Unknown research reference identity")
        expected_scope = f"{territory}:{reference_key}"
    elif reference_key is not None:
        raise ValueError("Reference identity is only valid for reference ingestion")
    if scope != expected_scope:
        raise ValueError("Unsupported ingestion territory or scope")
    return reference


def _result(execution, *, reused=False):
    return {
        "execution_id": str(execution.pk),
        "execution_key": execution.execution_key,
        "operation": execution.operation,
        "scope": execution.scope,
        "actor": execution.actor,
        "status": execution.status,
        "summary": execution.summary,
        "run_ids": sorted(str(value) for value in execution.runs.values_list("pk", flat=True)),
        "reused": reused or execution.reused_from_id is not None,
        "reused_from": str(execution.reused_from_id) if execution.reused_from_id else None,
        "attempts": execution.attempts,
        "error": execution.error,
        "started_at": execution.started_at.isoformat(),
        "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
        "prefect_flow_run_id": (
            str(execution.prefect_flow_run_id) if execution.prefect_flow_run_id else None
        ),
    }


def execution_result(*, execution_key, operation, scope, actor, include_failed=False):
    """Short-circuit a committed retry before performing a fresh acquisition."""
    _validate_identity(operation, scope, execution_key, actor)
    execution = IngestionExecution.objects.filter(execution_key=execution_key).first()
    if execution is None:
        return None
    if (execution.operation, execution.scope, execution.actor) != (operation, scope, actor.strip()):
        raise ValueError("Execution identity already belongs to another request")
    terminal = TERMINAL | ({"failed"} if include_failed else set())
    return _result(execution, reused=True) if execution.status in terminal else None


def record_acquisition_failure(
    *,
    operation,
    scope,
    execution_key,
    actor,
    error,
    prefect_flow_run_id=None,
    received_acquisitions=None,
):
    """Record precollection failure without inventing a source response or source run."""
    _validate_identity(operation, scope, execution_key, actor)
    actor = actor.strip()
    if connection.vendor != "postgresql":
        raise ValueError("Ingestion orchestration requires PostgreSQL/PostGIS")
    if prefect_flow_run_id is not None:
        prefect_flow_run_id = uuid.UUID(str(prefect_flow_run_id))
    completed_receipts = validate_received_acquisitions(operation, scope, received_acquisitions)
    name = type(error).__name__ if isinstance(error, BaseException) else error
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,159}", name):
        name = "AcquisitionError"
    lock = services.LOCK_KEY if operation == "onwani" else map_import.LOCK_KEY
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [lock])
        if not cursor.fetchone()[0]:
            raise ImportBusy("Source acquisition already running")
    try:
        with transaction.atomic():
            execution = IngestionExecution.objects.filter(execution_key=execution_key).first()
            if execution is not None:
                if (execution.operation, execution.scope, execution.actor) != (
                    operation,
                    scope,
                    actor,
                ):
                    raise ValueError("Execution identity already belongs to another request")
                if execution.status in TERMINAL:
                    return _result(execution, reused=True)
                execution.attempts += 1
            else:
                execution = IngestionExecution.objects.create(
                    execution_key=execution_key,
                    operation=operation,
                    scope=scope,
                    actor=actor,
                    prefect_flow_run_id=prefect_flow_run_id,
                )
            execution.status, execution.error = "failed", name
            execution.summary = {"phase": "acquisition"}
            if completed_receipts:
                namespace, source_name, url, version = source_definition(operation, scope)
                source, _ = Source.objects.get_or_create(
                    key=namespace,
                    defaults={"name": source_name, "url": url},
                )
                run = IngestionRun.objects.create(
                    source=source, actor=actor, connector_version=version
                )
                for payload, receipt in completed_receipts:
                    Capture.objects.create(
                        run=run,
                        payload=payload,
                        byte_length=len(payload),
                        content_sha256=hashlib.sha256(payload).hexdigest(),
                        **receipt,
                    )
                run.status, run.error, run.finished_at = "failed", name, timezone.now()
                run.summary = {
                    "phase": "acquisition",
                    "capture_count": len(completed_receipts),
                    "http_statuses": sorted(
                        {receipt["http_status"] for _, receipt in completed_receipts}
                    ),
                }
                run.save(update_fields=["status", "error", "finished_at", "summary"])
                execution.runs.add(run)
                execution.summary = run.summary
            execution.finished_at = timezone.now()
            execution.save(update_fields=["status", "error", "summary", "finished_at", "attempts"])
        return _result(execution)
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [lock])


def _fingerprint(operation, receipt, territory=DEFAULT_TERRITORY):
    if operation not in {"property_presentations", "imagery"}:
        if receipt is not None:
            raise ValueError("Receipt input is only valid for inert property/imagery imports")
        return None
    if (
        not isinstance(receipt, list)
        or not receipt
        or any(not isinstance(row, dict) for row in receipt)
    ):
        raise ValueError("A bounded receipt list is required")
    value = {
        "operation": operation,
        "receipts": sorted(receipt, key=lambda row: row.get("url", "")),
    }
    if operation == "property_presentations":
        value["review_version"] = property_import.VERSION
        value["registry"] = property_import.registry(territory)
    else:
        value["render_version"] = "reem-sentinel-crop-v1"
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    maximum = 32 * 1024 * 1024 if operation == "property_presentations" else 16 * 1024 * 1024
    if len(encoded) > maximum:
        raise ValueError("Receipt input exceeds acquisition budget")
    # Times are intentionally included: a genuinely fresh check is distinct from replay.
    return hashlib.sha256(encoded).hexdigest()


def _source_keys(operation, scope, reference):
    territory = scope.split(":", 1)[0]
    profile = collection_for(territory)
    if operation == "osm_bootstrap":
        return [profile.map_namespace("osm")]
    if operation == "onwani":
        return [profile.parcel_namespace]
    if operation == "map":
        layer = scope.rsplit(":", 1)[1]
        return [profile.map_namespace(layer)]
    if operation == "references":
        return ["research:" + reference_identity(reference["url"])]
    if operation == "property_presentations":
        profiles, _ = property_import.registry(territory)
        return ["property:" + reference_identity(row["source_url"]) for row in profiles]
    return ["sentinel:" + identity for identity in imagery_import.SCENES]


def _dispatch(operation, scope, actor, acquisition, receipt, reference):
    territory = scope.split(":", 1)[0]
    if operation == "osm_bootstrap":
        run = osm_bootstrap.import_bootstrap(
            territory=territory, actor=actor, acquisition=acquisition
        )
        return run.status, run.summary
    if operation == "onwani":
        run = services.import_onwani(actor=actor, acquisition=acquisition, territory=territory)
        return run.status, run.summary
    if operation == "map":
        run = map_import.import_map_layer(
            layer=scope.rsplit(":", 1)[1], actor=actor, acquisition=acquisition, territory=territory
        )
        return run.status, run.summary
    if operation == "references":
        run = research_import.import_reference(
            reference, actor=actor, acquisition=acquisition, territory=territory
        )
        return run.status, run.summary
    if operation == "property_presentations":
        presentations = property_import.import_presentations(
            receipt,
            actor=actor,
            profiles=property_import.registry(territory)[0],
            photos=property_import.registry(territory)[1],
        )
        return "succeeded", {"presentations": len(presentations)}
    runs = imagery_import.import_imagery(receipt, actor=actor)
    return "succeeded", {
        "scenes": len(runs),
        "created": sum(run.summary["created"] for run in runs),
        "unchanged": sum(not run.summary["created"] for run in runs),
    }


def execute_import(
    *,
    operation,
    scope,
    execution_key,
    actor,
    acquisition=None,
    receipt=None,
    reference_key=None,
    prefect_flow_run_id=None,
    completion_check=None,
):
    """Execute one allowlisted operation, with durable retry and receipt identities.

    Failure is a returned terminal result, not an exception after successful writes.
    Delivery adapters must map failed/quarantined results to visible Prefect states.
    Busy/invalid identity errors are raised before creating an operational record.
    """
    reference = _validate_identity(operation, scope, execution_key, actor, reference_key)
    actor = actor.strip()
    if connection.vendor != "postgresql":
        raise ValueError("Ingestion orchestration requires PostgreSQL/PostGIS")
    if prefect_flow_run_id is not None:
        prefect_flow_run_id = uuid.UUID(str(prefect_flow_run_id))
    fingerprint = _fingerprint(operation, receipt, scope.split(":", 1)[0])
    lock = services.LOCK_KEY if operation == "onwani" else map_import.LOCK_KEY
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [lock])
        if not cursor.fetchone()[0]:
            raise ImportBusy("Source acquisition already running")
    try:
        execution = IngestionExecution.objects.filter(execution_key=execution_key).first()
        if execution is not None:
            if (execution.operation, execution.scope, execution.actor) != (operation, scope, actor):
                raise ValueError("Execution identity already belongs to another request")
            if execution.status in TERMINAL:
                return _result(execution, reused=True)
            if execution.input_sha256 != fingerprint and not (
                execution.input_sha256 is None and execution.summary.get("phase") == "acquisition"
            ):
                # Validate a bound failed attempt before considering another job's
                # exact receipt. Reuse must never rebind this execution identity.
                raise ValueError("Retry receipt differs from its original execution")
        if fingerprint is not None:
            prior = IngestionExecution.objects.filter(
                operation=operation,
                scope=scope,
                input_sha256=fingerprint,
                status__in=TERMINAL,
            ).first()
            if prior is not None:
                # A new Prefect run owns a new operational identity even when its
                # exact receipt reuses historical evidence. Never rewrite source dates.
                with transaction.atomic():
                    if execution is None:
                        execution = IngestionExecution.objects.create(
                            execution_key=execution_key,
                            operation=operation,
                            scope=scope,
                            actor=actor,
                            prefect_flow_run_id=prefect_flow_run_id,
                        )
                    else:
                        execution.attempts += 1
                    if completion_check is not None:
                        completion_check()
                    execution.input_sha256 = None
                    execution.reused_from = prior
                    execution.status = prior.status
                    execution.summary = prior.summary
                    execution.error = ""
                    execution.finished_at = timezone.now()
                    execution.runs.set(prior.runs.all())
                    execution.save(
                        update_fields=[
                            "attempts",
                            "input_sha256",
                            "reused_from",
                            "status",
                            "summary",
                            "error",
                            "finished_at",
                        ]
                    )
                return _result(execution, reused=True)
        if execution is not None:
            if execution.input_sha256 is None and execution.summary.get("phase") == "acquisition":
                # No complete receipt existed in a transport failure; bind it on recovery.
                execution.input_sha256 = fingerprint
                execution.save(update_fields=["input_sha256"])
        if execution is None:
            execution = IngestionExecution.objects.create(
                execution_key=execution_key,
                operation=operation,
                scope=scope,
                actor=actor,
                input_sha256=fingerprint,
                prefect_flow_run_id=prefect_flow_run_id,
            )
        else:
            IngestionExecution.objects.filter(pk=execution.pk).update(
                attempts=F("attempts") + 1, status="running", finished_at=None, error=""
            )
            execution.refresh_from_db()
        started = timezone.now()
        source_keys = _source_keys(operation, scope, reference)
        try:
            with transaction.atomic():
                error = ""
                try:
                    status, summary = _dispatch(
                        operation, scope, actor, acquisition, receipt, reference
                    )
                except Exception as exc:
                    if connection.needs_rollback:
                        raise
                    # Existing services have already rolled back canonical writes. Preserve
                    # their failed capture/run evidence and commit the operational outcome.
                    status, summary, error = "failed", {}, type(exc).__name__
                runs = list(
                    IngestionRun.objects.filter(
                        source__key__in=source_keys, actor=actor, started_at__gte=started
                    )
                )
                if status == "failed" and not error:
                    error = next((run.error for run in runs if run.error), "SourceUnavailable")
                if completion_check is not None and status in TERMINAL:
                    # A staging/protocol mismatch must roll back canonical writes too.
                    completion_check()
                execution.runs.add(*runs)
                execution.status, execution.summary, execution.error = status, summary, error
                execution.finished_at = timezone.now()
                execution.save(update_fields=["status", "summary", "error", "finished_at"])
        except Exception as exc:
            # A database failure or completion-marker failure rolls back canonical writes,
            # so a retry is safe. Diagnostics never include SQL, payloads or credentials.
            execution.status, execution.error = "failed", type(exc).__name__
            execution.summary, execution.finished_at = {}, timezone.now()
            execution.save(update_fields=["status", "error", "summary", "finished_at"])
        return _result(execution)
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [lock])
