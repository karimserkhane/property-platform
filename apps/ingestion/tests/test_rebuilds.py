"""A rebuild owns only its generated database; failures must still clean that up."""

import json
from contextlib import contextmanager
from uuid import uuid4

import pytest

from property_platform_ingestion import rebuilds
from property_platform_ingestion.registry import DATASETS

URL = "postgresql://user:p%40ss@db:5432/property_platform"


@pytest.mark.parametrize(
    "name",
    [
        "property_platform",
        "test_property_platform",
        "rebuild_check_x",
        "rebuild_check_" + "a" * 32 + ";drop database postgres",
    ],
)
def test_rebuild_target_cannot_be_an_existing_database_or_sql(name):
    with pytest.raises(ValueError):
        rebuilds.scratch_url(URL, name)


def test_target_keeps_credentials_private_and_drops_database_override_options():
    name = "rebuild_check_" + "a" * 32
    assert rebuilds.scratch_url(URL, name) == f"postgresql://user:p%40ss@db:5432/{name}"
    for suffix in ("?dbname=property_platform", "#other"):
        with pytest.raises(ValueError):
            rebuilds.scratch_url(URL + suffix, name)
    with pytest.raises(ValueError):
        rebuilds.scratch_url(f"postgresql://db/{name}", name)


@pytest.mark.parametrize("failure", [None, "export", "create", "replay"])
def test_only_the_database_created_by_this_run_is_dropped(tmp_path, monkeypatch, failure):
    actions, sql_statements = [], []
    monkeypatch.setattr(rebuilds, "backup_root", lambda: tmp_path)

    def worker(action, root, url, **kwargs):
        actions.append((action, url, kwargs))
        if failure == action:
            raise RuntimeError("worker failure")
        (root / "manifest.json").write_text('{"version":1}')
        (root / "report.json").write_text(
            json.dumps(
                {
                    "ok": False,
                    "tables": [],
                    "failed_steps": 1,
                    "mismatches": ["real_estate.parcel"],
                    "source_snapshot_at": "2026-10-23T00:00:00+00:00",
                }
            )
        )

    class Admin:
        def execute(self, query):
            sql_statements.append(query.as_string())
            if failure == "create" and query.as_string().startswith("CREATE"):
                raise RuntimeError("create failed")

    @contextmanager
    def connect(url, **kwargs):
        assert url == URL
        yield Admin()

    monkeypatch.setattr(rebuilds, "worker", worker)
    monkeypatch.setattr(rebuilds.psycopg, "connect", connect)
    if failure:
        with pytest.raises(RuntimeError):
            rebuilds.rebuild_check(actor="test", run_id=str(uuid4()), url=URL)
    else:
        result = rebuilds.rebuild_check(actor="test", run_id=str(uuid4()), url=URL)
        assert not result["ok"]
        assert "p%40ss" not in json.dumps(result)
    expected_sql = 0 if failure == "export" else 1 if failure == "create" else 2
    assert len(sql_statements) == expected_sql
    if expected_sql == 2:
        name = sql_statements[0].split('"')[1]
        assert rebuilds.SCRATCH.fullmatch(name)
        assert sql_statements[-1] == f'DROP DATABASE "{name}"'
    if len(actions) == 2:
        assert actions[0][1] == URL
        assert actions[1][1] != URL
        assert len(actions[1][2]["manifest_hash"]) == 64


def test_rebuild_check_is_manual_and_does_not_start_another_scheduled_collection():
    dataset = next(d for d in DATASETS if d.name == "rebuild-check")
    assert dataset.flow_name == "property-platform-rebuild-check"
    assert dataset.cron is None
    assert dataset.parameters == {}


def test_prefect_flow_fails_when_the_report_is_incomplete(monkeypatch):
    from types import SimpleNamespace

    from property_platform_ingestion import flows
    from property_platform_ingestion.runtime import IngestionFailure

    monkeypatch.setattr(flows, "flow_run", SimpleNamespace(id=str(uuid4())))
    monkeypatch.setattr(flows, "get_run_logger", lambda: SimpleNamespace(info=lambda *args: None))
    monkeypatch.setattr(rebuilds, "rebuild_check", lambda **kwargs: {"ok": False})
    with pytest.raises(IngestionFailure, match="IncompleteSourceRebuild"):
        flows.rebuild_check.fn()


@pytest.mark.parametrize(
    "actual_name,has_tables,accepted",
    [
        ("rebuild_check_" + "a" * 32, False, True),
        ("rebuild_check_" + "a" * 32, True, False),
        ("property_platform", False, False),
    ],
)
def test_worker_checks_the_actual_connection_and_emptiness_before_migrations(
    actual_name, has_tables, accepted
):
    from types import SimpleNamespace

    from property_platform_ingestion.rebuild_worker import require_empty_target

    @contextmanager
    def cursor():
        yield SimpleNamespace(
            execute=lambda query: None, fetchone=lambda: (actual_name, has_tables)
        )

    connection = SimpleNamespace(cursor=cursor)
    if accepted:
        require_empty_target(connection, "rebuild_check_" + "a" * 32)
    else:
        with pytest.raises(ValueError, match="own completely empty"):
            require_empty_target(connection, "rebuild_check_" + "a" * 32)
