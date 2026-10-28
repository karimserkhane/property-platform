from types import SimpleNamespace

import pytest

from property_platform_ingestion import flows
from property_platform_ingestion.registry import DATASETS


def test_presentations_archive_only_after_the_audited_import_completes(monkeypatch):
    calls = []

    def ingest(operation, scope, actor):
        calls.append((operation, scope, actor))
        return {"status": "succeeded", "reused": True}

    def archive(actor):
        calls.append(("archive", actor))
        return {"status": "succeeded", "summary": {"archived": 2}}

    monkeypatch.setattr(flows, "ingest_source", ingest)
    monkeypatch.setattr(flows, "archive_media", archive)
    result = flows.presentations.fn(territory="saadiyat-island", actor="test")
    assert calls == [("property_presentations", "saadiyat-island", "test"), ("archive", "test")]
    assert result["media_storage"]["summary"]["archived"] == 2


def test_failed_source_import_does_not_start_media_archival(monkeypatch):
    def fail(*args):
        raise ValueError("Source rejected")

    monkeypatch.setattr(flows, "ingest_source", fail)
    monkeypatch.setattr(flows, "archive_media", lambda *args: pytest.fail("Must not archive"))
    with pytest.raises(ValueError):
        flows.presentations.fn()


def test_media_task_is_private_audited_and_not_cached(monkeypatch):
    requests = []
    monkeypatch.setattr(flows, "flow_run", SimpleNamespace(id="test-flow"))
    monkeypatch.setattr(flows, "get_run_logger", lambda: SimpleNamespace(info=lambda *a: None))
    monkeypatch.setattr(
        flows,
        "invoke_domain",
        lambda request: (
            requests.append(request)
            or {
                "status": "succeeded",
                "summary": {"archived": 1},
            }
        ),
    )
    flows.archive_media.fn("Karim")
    assert requests == [
        {
            "operation": "media_storage",
            "actor": "Prefect/test-flow/Karim",
            "prefect_flow_run_id": "test-flow",
        }
    ]
    deployment = next(row for row in DATASETS if row.name == "media-storage")
    assert deployment.cron is None
    assert "publish" not in deployment.parameters
