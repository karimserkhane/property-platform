"""Portable source history, integrity checks and adoption without the previous DB."""

import base64
import copy
import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from test_project_psi import fixture, payload

from property_platform_ingestion.project_archive import (
    archive_catalogue_batch,
    archive_project_batch,
    catalogue_batches,
    index_project_checkpoints,
    project_batches,
    project_source_scope,
    read_catalogue_batch,
    read_project_batch,
)
from property_platform_ingestion.storage import stored_property_receipt


def acquisition():
    project, source, data = fixture()
    raw = payload(data)
    now = datetime.now(UTC) - timedelta(days=2)
    receipt = {
        "url": source["url"],
        "payload": base64.b64encode(raw).decode(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "fetched_started_at": now.isoformat(),
        "fetched_at": now.isoformat(),
        "http_status": 200,
    }
    return project_source_scope(project, source), [receipt]


def test_source_archive_keeps_exact_bytes_dates_and_all_historical_versions(tmp_path):
    scope, rows = acquisition()
    old = archive_project_batch(tmp_path, scope, rows)
    assert archive_project_batch(tmp_path, scope, rows) == old
    fresh = copy.deepcopy(rows)
    fresh[0]["fetched_at"] = datetime.now(UTC).isoformat()
    new = archive_project_batch(tmp_path, scope, fresh)
    assert new != old
    assert project_batches(tmp_path, scope) == (old, new)
    assert read_project_batch(tmp_path, scope, old) == rows
    assert read_project_batch(tmp_path, scope, new) == fresh


def test_ordinary_collector_checkpoints_can_be_indexed_without_a_database(tmp_path):
    scope, rows = acquisition()
    stored_property_receipt(tmp_path, "c" * 64, lambda: rows)
    result = index_project_checkpoints(tmp_path)
    assert result == {"checkpoints": 1, "indexed": 1, "rejected": 0}
    assert len(project_batches(tmp_path, scope)) == 1
    key = project_batches(tmp_path, scope)[0]
    assert read_project_batch(tmp_path, scope, key) == rows


def test_tampered_proof_cannot_be_imported_as_a_preserved_source(tmp_path):
    scope, rows = acquisition()
    key = archive_project_batch(tmp_path, scope, rows)
    path = next((tmp_path / "project-source-archive").glob("*/*.json"))
    path.write_text(path.read_text().replace("202", "201", 1))
    with pytest.raises(ValueError, match="integrity"):
        read_project_batch(tmp_path, scope, key)
    with pytest.raises(ValueError, match="identity"):
        read_project_batch(tmp_path, scope, "../outside")


def test_source_history_never_accepts_a_different_project_or_changed_raw_bytes(tmp_path):
    scope, rows = acquisition()
    rows[0]["payload"] = base64.b64encode(b"a different page").decode()
    with pytest.raises(ValueError, match="hash or size"):
        archive_project_batch(tmp_path, scope, rows)
    assert project_batches(tmp_path, scope) == ()
    with pytest.raises(ValueError, match="one reviewed"):
        archive_project_batch(tmp_path, "al-reem-island", rows)


def test_catalogue_history_rebuilds_original_discovery_even_when_publisher_is_gone(tmp_path):
    from property_platform.modules.evidence.project_discovery import catalogue_for
    from test_project_discovery import aldar_catalogue

    scope = "saadiyat-island:aldar-saadiyat"
    definition = catalogue_for(scope)
    _, rows = acquisition()
    rows[0].update(
        url=definition["url"],
        payload=base64.b64encode(aldar_catalogue()).decode(),
        sha256=hashlib.sha256(aldar_catalogue()).hexdigest(),
    )
    old = archive_catalogue_batch(tmp_path, scope, rows)
    newer = copy.deepcopy(rows)
    newer[0]["fetched_at"] = datetime.now(UTC).isoformat()
    new = archive_catalogue_batch(tmp_path, scope, newer)
    assert catalogue_batches(tmp_path, scope) == (old, new)
    assert read_catalogue_batch(tmp_path, scope, old) == rows
    with pytest.raises(ValueError):
        archive_catalogue_batch(tmp_path, "al-reem-island:aldar-reem", rows)
    path = next((tmp_path / "project-catalogue-archive").glob("*/*.json"))
    path.write_text(path.read_text().replace("202", "201", 1))
    with pytest.raises(ValueError, match="integrity"):
        catalogue_batches(tmp_path, scope)
