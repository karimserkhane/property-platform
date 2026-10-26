"""Project acquisition retries and operational markers on actual PostgreSQL."""

import base64
import copy
import hashlib
import os
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Project orchestration requires real PostGIS", allow_module_level=True)

from property_platform.modules.evidence import orchestration  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    IngestionExecution,
    IngestionRun,
    Source,
)
from property_platform.modules.evidence.projects import project_import, project_protocol  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def rows():
    payload = b"<html><title>Project receipt</title></html>"
    now = timezone.now() - timedelta(seconds=1)
    return [
        {
            "url": project_protocol.project_registry("al-reem-island")[0]["website_url"],
            "payload": base64.b64encode(payload).decode(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "http_status": 200,
            "fetched_started_at": now.isoformat(),
            "fetched_at": now.isoformat(),
        }
    ]


def execute(receipt, identity="first", **kwargs):
    return orchestration.execute_import(
        operation="project_details",
        scope="al-reem-island",
        actor="project-test",
        execution_key=hashlib.sha256(identity.encode()).hexdigest(),
        receipt=receipt,
        **kwargs,
    )


def source_write(receipts, *, actor, territory):
    assert territory == "al-reem-island"
    provider, _ = Source.objects.get_or_create(
        key="project:the-district", defaults={"name": "Reportage", "url": receipts[0]["url"]}
    )
    run = IngestionRun.objects.create(
        source=provider,
        actor=actor,
        connector_version=project_import.VERSION,
    )
    run.status, run.finished_at = "succeeded", timezone.now()
    run.save(update_fields=["status", "finished_at"])
    item = receipts[0]
    payload = base64.b64decode(item["payload"])
    Capture.objects.create(
        run=run,
        url=item["url"],
        payload=payload,
        byte_length=len(payload),
        content_sha256=item["sha256"],
        http_status=200,
        fetched_started_at=datetime.fromisoformat(item["fetched_started_at"]),
        fetched_at=datetime.fromisoformat(item["fetched_at"]),
    )
    return {"projects": 1, "snapshots": 1, "run_ids": [str(run.pk)]}


def test_exact_project_replay_preserves_source_bytes_dates_and_operational_identity(monkeypatch):
    importer = Mock(side_effect=source_write)
    monkeypatch.setattr(project_import, "import_project_details", importer)
    receipt = rows()
    first = execute(receipt)
    before = list(Capture.objects.values("pk", "fetched_at", "content_sha256"))
    same_job = execute(receipt)
    replay = execute(copy.deepcopy(receipt), "another-prefect-run")
    assert first["status"] == same_job["status"] == replay["status"] == "succeeded"
    assert same_job["execution_id"] == first["execution_id"]
    assert replay["execution_id"] != first["execution_id"]
    assert replay["reused_from"] == first["execution_id"]
    assert importer.call_count == 1
    assert replay["run_ids"] == first["run_ids"] and len(first["run_ids"]) == 1
    assert Capture.objects.count() == IngestionRun.objects.count() == 1
    assert IngestionExecution.objects.count() == 2
    assert list(Capture.objects.values("pk", "fetched_at", "content_sha256")) == before


def test_fresh_project_check_keeps_a_new_acquisition_without_rewriting_old_dates(monkeypatch):
    monkeypatch.setattr(project_import, "import_project_details", source_write)
    original = rows()
    first = execute(original)
    fresh = copy.deepcopy(original)
    now = timezone.now()
    fresh[0].update(fetched_started_at=now.isoformat(), fetched_at=now.isoformat())
    second = execute(fresh, "fresh")
    assert not second["reused"] and second["run_ids"] != first["run_ids"]
    assert Capture.objects.count() == 2
    assert Capture.objects.earliest("fetched_at").fetched_at == datetime.fromisoformat(
        original[0]["fetched_at"]
    )


def test_parser_version_changes_fingerprint_and_reused_source_runs_stay_linked(monkeypatch):
    monkeypatch.setattr(project_import, "import_project_details", source_write)
    receipt = rows()
    first = execute(receipt)
    old_fingerprint = IngestionExecution.objects.get(pk=first["execution_id"]).input_sha256
    monkeypatch.setattr(project_protocol, "PARSER_VERSION", "project-facts-v-next")
    importer = Mock(
        return_value={"projects": 1, "snapshots": 0, "reused": 1, "run_ids": first["run_ids"]}
    )
    monkeypatch.setattr(project_import, "import_project_details", importer)
    next_version = execute(receipt, "next-version")
    assert next_version["status"] == "succeeded" and not next_version["reused"]
    assert next_version["run_ids"] == first["run_ids"]
    assert (
        IngestionExecution.objects.get(pk=next_version["execution_id"]).input_sha256
        != old_fingerprint
    )
    assert Capture.objects.count() == 1 and importer.call_count == 1


def test_project_completion_failure_rolls_back_source_writes_and_marker_together(monkeypatch):
    monkeypatch.setattr(project_import, "import_project_details", source_write)
    result = execute(rows(), completion_check=Mock(side_effect=ValueError("Staging mismatch")))
    assert result["status"] == "failed"
    assert result["run_ids"] == []
    assert not Capture.objects.exists() and not IngestionRun.objects.exists()


def test_failed_project_html_is_audited_but_an_unregistered_binary_url_is_rejected():
    now = timezone.now()
    receipt = {
        "url": project_protocol.project_registry("al-reem-island")[0]["website_url"],
        "http_status": 503,
        "fetched_started_at": now,
        "fetched_at": now,
        "etag": "",
        "last_modified_raw": "",
        "acquisition_method": "scheduled_https_collect",
        "timestamp_basis": "collector_clock",
    }
    identity = {
        "operation": "project_details",
        "scope": "al-reem-island",
        "actor": "project-test",
        "execution_key": hashlib.sha256(b"failed-project").hexdigest(),
        "error": "SourceError",
    }
    result = orchestration.record_acquisition_failure(
        **identity, received_acquisitions=[{"payload": b"Actual failure", "receipt": receipt}]
    )
    assert result["status"] == "failed" and result["summary"]["capture_count"] == 1
    captured = Capture.objects.get()
    assert captured.url == receipt["url"] and bytes(captured.payload) == b"Actual failure"
    assert captured.fetched_at == now and captured.http_status == 503
    receipt["url"] = "https://vimeo.com/1038853770"
    with pytest.raises(ValueError, match="reviewed HTML"):
        orchestration.record_acquisition_failure(
            **identity, received_acquisitions=[{"payload": b"Must not fetch", "receipt": receipt}]
        )
    assert Capture.objects.count() == 1


def test_project_fingerprint_is_bounded_and_unknown_scope_cannot_create_a_job():
    with pytest.raises(ValueError, match="budget"):
        orchestration._fingerprint("project_details", [{"payload": "x" * (32 * 1024 * 1024)}])
    with pytest.raises(ValueError):
        orchestration.execute_import(
            operation="project_details",
            scope="al-reem-island:unreviewed",
            actor="project-test",
            execution_key="a" * 64,
            receipt=rows(),
        )
    assert not IngestionExecution.objects.exists()


def test_changed_reading_code_reads_archived_bytes_again(monkeypatch):
    # A replay of the same receipt after an extractor change (B02 register facts)
    # must reach the importer instead of reusing the earlier execution.
    monkeypatch.setattr(project_import, "import_project_details", source_write)
    receipt = rows()
    first = execute(receipt)
    unchanged = execute(copy.deepcopy(receipt), "same-code")
    assert unchanged["reused_from"] == first["execution_id"]
    monkeypatch.setattr(project_import, "interpretation_sha256", lambda: "0" * 64)
    importer = Mock(
        return_value={"projects": 1, "snapshots": 1, "reused": 0, "run_ids": first["run_ids"]}
    )
    monkeypatch.setattr(project_import, "import_project_details", importer)
    reread = execute(copy.deepcopy(receipt), "new-code")
    assert reread["status"] == "succeeded" and not reread["reused"]
    assert importer.call_count == 1
