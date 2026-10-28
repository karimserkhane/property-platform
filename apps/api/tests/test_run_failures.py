import logging
from types import SimpleNamespace

from property_platform.modules.evidence.runs import mark_failed


def test_failed_run_stores_error_class_only_and_logs_traceback(caplog):
    saved = []
    run = SimpleNamespace(pk=7, save=lambda update_fields: saved.append(update_fields))
    error = ValueError("https://source.example/data?token=private")
    with caplog.at_level(logging.ERROR, logger="property_platform.modules.evidence.runs"):
        mark_failed(run, error)
    assert (run.status, run.error) == ("failed", "ValueError")
    assert run.finished_at is not None
    assert saved == [["status", "error", "finished_at"]]
    [record] = caplog.records
    assert record.exc_info[1] is error
    assert "private" not in record.getMessage()


def test_traceback_is_logged_even_when_status_update_fails(caplog):
    def reject(update_fields):
        raise RuntimeError("database unavailable")

    run = SimpleNamespace(pk=8, save=reject)
    with caplog.at_level(logging.ERROR, logger="property_platform.modules.evidence.runs"):
        try:
            mark_failed(run, KeyError("feature"))
        except RuntimeError:
            pass
    [record] = caplog.records
    assert record.exc_info[0] is KeyError
