"""Own a bounded domain subprocess: no ORM on the Prefect event-loop thread."""

import json
import re
import subprocess
import sys
from pathlib import Path

MAX_REQUEST = 8192
MAX_RESULT = 64 * 1024
TIMEOUT = 900


class IngestionFailure(RuntimeError):
    def __init__(self, result):
        self.result = result
        super().__init__(f"Ingestion failed: {result.get('error', 'UnknownFailure')}")


def _decode(process):
    if len(process.stdout.encode()) > MAX_RESULT:
        raise ValueError("Oversized domain response")
    result = json.loads(process.stdout)
    if not isinstance(result, dict) or result.get("status") not in {
        "succeeded",
        "quarantined",
        "failed",
    }:
        raise ValueError("Invalid domain status")
    return result


def _reconcile(request, error):
    identity_fields = ("operation", "scope", "execution_key", "actor")
    if request.get("operation") == "check" or not all(key in request for key in identity_fields):
        raise IngestionFailure({"status": "failed", "error": error})
    reconciliation = {key: request[key] for key in identity_fields}
    reconciliation.update(
        action="reconcile", error=error, prefect_flow_run_id=request.get("prefect_flow_run_id")
    )
    try:
        process = subprocess.run(
            [sys.executable, "-m", "property_platform_ingestion.domain"],
            input=json.dumps(reconciliation),
            stdout=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
        result = _decode(process)
    except subprocess.TimeoutExpired, ValueError, OSError:
        raise IngestionFailure({"status": "failed", "error": error}) from None
    if process.returncode or result["status"] == "failed":
        raise IngestionFailure(result)
    return result


def checked_receipt_path(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\.json", name):
        raise ValueError("Receipt must be a filename in the ingestion storage directory")
    path = (root / name).resolve()
    if path.parent != root.resolve():
        raise ValueError("Receipt escapes ingestion storage")
    return path


def invoke_domain(request: dict, *, timeout: int = TIMEOUT) -> dict:
    encoded = json.dumps(request)
    if len(encoded.encode()) > MAX_REQUEST:
        raise ValueError("Domain request exceeds its budget")
    # No shell, arbitrary command, URL or credential is accepted in parameters. Only stdout
    # carries the result; stderr is inherited so domain tracebacks reach the runner's
    # container log and never a flow result or Prefect UI message.
    try:
        process = subprocess.run(
            [sys.executable, "-m", "property_platform_ingestion.domain"],
            input=encoded,
            stdout=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        # subprocess.run terminates and waits for the child. Closing its DB session
        # releases source locks; the backend commits writes with the completion marker.
        return _reconcile(request, "DomainTimeout")
    try:
        result = _decode(process)
    except ValueError, TypeError:
        # Never echo child output into the result: only the diagnostic class is kept.
        return _reconcile(request, "InvalidDomainResponse")
    if process.returncode or result["status"] == "failed":
        raise IngestionFailure(result)
    return result
