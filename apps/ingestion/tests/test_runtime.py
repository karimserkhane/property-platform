import json
import os
import subprocess
from types import SimpleNamespace

import pytest

from property_platform_ingestion.registry import DATASETS, execution_identity
from property_platform_ingestion.runtime import (
    IngestionFailure,
    checked_receipt_path,
    invoke_domain,
)
from property_platform_ingestion.storage import stored_property_receipt


def test_stable_execution_identity_is_scoped_to_run_source_and_version():
    key = execution_identity("run", "map", "area:osm")
    assert key == execution_identity("run", "map", "area:osm")
    assert key != execution_identity("run", "map", "area:street")
    assert key != execution_identity("another-run", "map", "area:osm")
    assert len(key) == 64


@pytest.mark.parametrize(
    "name",
    [
        "../secret.json",
        "/private.json",
        "C:\\secret.json",
        "https://evil.example/a.json",
        "a/b.json",
        "a.env",
    ],
)
def test_operator_receipt_name_cannot_escape_private_storage(tmp_path, name):
    with pytest.raises(ValueError):
        checked_receipt_path(tmp_path, name)


def test_operator_receipt_symlink_cannot_escape_storage(tmp_path):
    target = tmp_path.parent / "outside.json"
    target.write_text("[]")
    try:
        (tmp_path / "receipt.json").symlink_to(target)
    except OSError:
        pytest.skip("Host does not permit symlink creation")
    with pytest.raises(ValueError):
        checked_receipt_path(tmp_path, "receipt.json")


def test_exact_acquired_receipt_survives_retry_without_new_source_dates(tmp_path):
    key = "a" * 64
    rows = [{"url": "https://source.example", "fetched_at": "original-date"}]
    assert stored_property_receipt(tmp_path, key, lambda: rows) == rows

    def unexpected_network():
        raise AssertionError("Retry should replay the acquired receipt")

    assert stored_property_receipt(tmp_path, key, unexpected_network) == rows
    assert not list((tmp_path / "receipts").glob("receipt-*"))


def test_partial_collection_is_not_saved_as_a_complete_receipt(tmp_path):
    def collect():
        raise TimeoutError()

    with pytest.raises(TimeoutError):
        stored_property_receipt(tmp_path, "b" * 64, collect)
    assert not list((tmp_path / "receipts").glob("*.json"))


def test_two_attempts_cannot_overwrite_the_first_complete_receipt(tmp_path, monkeypatch):
    first = [{"fetched_at": "first-collector-time"}]
    second = [{"fetched_at": "second-collector-time"}]

    def another_attempt_wins(source, destination):
        destination.write_text(json.dumps(first))
        raise FileExistsError()

    monkeypatch.setattr(os, "link", another_attempt_wins)
    assert stored_property_receipt(tmp_path, "c" * 64, lambda: second) == first
    assert not list((tmp_path / "receipts").glob("receipt-*"))


def test_history_and_static_assets_are_not_recurring_jobs():
    assert len({dataset.name for dataset in DATASETS}) == len(DATASETS) == 65
    # The source rights mirror contacts no source and follows the deployed registry daily.
    assert next(d for d in DATASETS if d.name == "source-rights").cron == "45 0 * * *"
    imagery = next(dataset for dataset in DATASETS if dataset.name == "sentinel-previews")
    assert imagery.cron is None
    for territory in ("reem", "saadiyat", "maryah"):
        job = next(dataset for dataset in DATASETS if dataset.name == f"{territory}-osm-bootstrap")
        assert job.cron is None
    assert not any("font" in dataset.name or "home" in dataset.name for dataset in DATASETS)
    assert next(d for d in DATASETS if d.name == "routing-osm-graph").cron == "0 3 1 * *"
    assert next(d for d in DATASETS if d.name == "walking-areas").cron == "* * * * *"


def test_domain_result_preserves_quarantine_as_an_explicit_non_retry_outcome(monkeypatch):
    response = {"status": "quarantined", "summary": {"quarantined": 1}}
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(response),
            stderr="",
        ),
    )
    assert invoke_domain({"operation": "onwani"}) == response


def test_domain_stderr_reaches_operator_logs_and_never_the_result(monkeypatch):
    def run(*args, **kwargs):
        assert kwargs["stdout"] is subprocess.PIPE
        assert "stderr" not in kwargs and not kwargs.get("capture_output")
        return SimpleNamespace(returncode=1, stdout='{"status": "failed", "error": "KeyError"}')

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(IngestionFailure) as error:
        invoke_domain({"operation": "onwani"})
    assert error.value.result == {"status": "failed", "error": "KeyError"}


def test_swallowed_django_source_failure_is_not_reported_as_success(monkeypatch):
    response = {"status": "failed", "error": "SourceUnavailable"}
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(response),
            stderr="private configuration",
        ),
    )
    with pytest.raises(IngestionFailure, match="SourceUnavailable"):
        invoke_domain({"operation": "references"})


def test_child_timeout_does_not_echo_connection_configuration(monkeypatch):
    def run(*args, **kwargs):
        assert kwargs["timeout"] == 5
        assert not kwargs.get("shell")
        raise subprocess.TimeoutExpired(args[0], 5, stderr="private configuration")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(IngestionFailure, match="DomainTimeout") as error:
        invoke_domain({"operation": "map"}, timeout=5)
    assert "private" not in str(error.value)


@pytest.mark.parametrize("mode", ["timeout", "lost-stdout"])
def test_uncertain_child_result_is_reconciled_without_recollecting(monkeypatch, mode):
    identity = {
        "operation": "map",
        "scope": "al-reem-island:osm",
        "execution_key": "a" * 64,
        "actor": "operator",
    }
    calls = []

    def run(*args, **kwargs):
        request = json.loads(kwargs["input"])
        calls.append(request)
        if len(calls) == 1:
            if mode == "timeout":
                raise subprocess.TimeoutExpired(args[0], 5)
            return SimpleNamespace(returncode=0, stdout="", stderr="private")
        assert request["action"] == "reconcile"
        assert kwargs["timeout"] == 30
        return SimpleNamespace(
            returncode=0,
            stderr="",
            stdout=json.dumps(
                {
                    "status": "succeeded",
                    "reused": True,
                    "execution_id": "previous",
                }
            ),
        )

    monkeypatch.setattr(subprocess, "run", run)
    result = invoke_domain(identity, timeout=5)
    assert result["reused"] is True
    assert len(calls) == 2
    assert calls[1]["execution_key"] == identity["execution_key"]


def test_failed_reconciliation_keeps_precise_backend_diagnostic(monkeypatch):
    calls = []

    def run(*args, **kwargs):
        calls.append(json.loads(kwargs["input"]))
        if len(calls) == 1:
            raise subprocess.TimeoutExpired(args[0], 5)
        return SimpleNamespace(
            returncode=1,
            stdout=json.dumps(
                {
                    "status": "failed",
                    "error": "SourceSchemaChanged",
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(IngestionFailure, match="SourceSchemaChanged"):
        invoke_domain(
            {
                "operation": "map",
                "scope": "al-reem-island:osm",
                "execution_key": "a" * 64,
                "actor": "operator",
            },
            timeout=5,
        )


def test_backups_run_nightly_and_restore_checks_weekly_once_enabled():
    flows = {d.name: (d.flow_name, d.cron) for d in DATASETS}
    assert flows["backup-database"] == ("property-platform-backup", "30 1 * * *")
    assert flows["restore-check"] == ("property-platform-restore-check", "0 5 * * 0")
