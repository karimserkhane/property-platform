"""History is tested on PostgreSQL triggers and real typed observations, not SQLite."""

import hashlib
import os
from datetime import timedelta
from types import SimpleNamespace

import pytest

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Database journals require PostgreSQL/PostGIS", allow_module_level=True)

from django.db import DatabaseError, transaction  # noqa: E402
from django.utils import timezone  # noqa: E402
from test_public_context_postgis import execute  # noqa: E402
from test_public_context_protocol import facility  # noqa: E402

from property_platform.modules.evidence.basemap_archive import (  # noqa: E402
    archive_pending,
    archived_tile,
)
from property_platform.modules.evidence.history.pipeline_inventory import inventory  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    BasemapRequest,
    Capture,
    HistoryExclusion,
    RowRevision,
    Source,
)
from property_platform.modules.publication.context_preview import public_context  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def test_every_owned_table_has_an_audit_trigger_and_a_pipeline_owner():
    report = inventory()
    assert len(report["tables"]) >= 40
    assert report["uncovered"] == []


def test_journal_survives_bulk_update_delete_and_rollback_and_excludes_binary_bytes():
    execute([facility()])
    capture = Capture.objects.get()
    journal = RowRevision.objects.get(
        table_name="capture", row_key=str(capture.pk), operation="INSERT"
    )
    assert journal.known_ingested_at == capture.ingested_at
    assert journal.recorded_at >= capture.ingested_at
    assert journal.execution_key and journal.actor == "test-context"
    assert "payload" not in journal.after
    source = Source.objects.create(key="audit-fixture", name="Before", url="https://example.com")
    Source.objects.filter(pk=source.pk).update(name="After")
    Source.objects.filter(pk=source.pk).delete()
    changes = list(
        RowRevision.objects.filter(table_name="source", row_key=str(source.pk)).order_by("id")
    )
    assert [r.operation for r in changes] == ["INSERT", "UPDATE", "DELETE"]
    assert changes[1].before["name"] == "Before" and changes[1].after["name"] == "After"
    assert changes[2].before["name"] == "After"
    with pytest.raises(ValueError), transaction.atomic():
        Source.objects.create(
            key="rolled-back", name="Invalid transaction", url="https://example.com"
        )
        raise ValueError("rollback")
    assert not RowRevision.objects.filter(after__key="rolled-back").exists()
    with pytest.raises(DatabaseError, match="append-only"), transaction.atomic():
        RowRevision.objects.filter(pk=journal.pk).update(actor="rewrite")
    with pytest.raises(DatabaseError, match="immutable"), transaction.atomic():
        Capture.objects.filter(pk=capture.pk).update(payload=b"replaced")
    with pytest.raises(DatabaseError, match="cannot be deleted"), transaction.atomic():
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM evidence.capture WHERE id=%s", [capture.pk])


def test_missing_context_records_and_fields_fall_back_without_relabelling_old_dates():
    execute([facility(i, FacilityOwnership="Original operator") for i in range(1, 6)])
    original = public_context("health")
    execute([facility(i, FacilityOwnership="") for i in range(1, 5)], "partial-success")
    result = public_context("health")
    assert result["total"] == 5
    archived = next(row for row in result["health"] if row["historical"])
    assert archived["retrieved_at"] == original["health"][0]["retrieved_at"]
    assert archived["snapshot_id"] != result["snapshot_id"]
    updated = next(row for row in result["health"] if not row["historical"])
    assert updated["operator"] == "Original operator" and "operator" in updated["field_history"]
    # A confirmed withdrawal is an explicit, evidence-backed operator decision.
    HistoryExclusion.objects.create(
        dataset="context:health",
        record_key=archived["source_record_id"],
        capture=Capture.objects.first(),
        actor="reviewer",
        reason="Authority confirmed withdrawal",
    )
    assert public_context("health")["total"] == 4


def tile_acquisition(payload, status=200):
    now = timezone.now()
    return SimpleNamespace(
        payload=payload,
        http_status=status,
        sha256=hashlib.sha256(payload).hexdigest(),
        capture_receipt=lambda: {
            "url": "https://wmts.terrascope.be/wmts?fixed=test",
            "http_status": status,
            "fetched_started_at": now,
            "fetched_at": now,
            "acquisition_method": "scheduled_https_collect",
            "timestamp_basis": "collector_clock",
        },
    )


def test_tile_offline_read_uses_immutable_bytes_and_failed_refresh_keeps_previous_version():
    import struct

    png = (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", 256, 256)
        + b"\0" * 9
    )
    provider = "sentinel-worldcover-2021"
    assert archived_tile(provider, 13, 5334, 3520) is None
    assert BasemapRequest.objects.count() == 1
    first = archive_pending(
        provider,
        actor="test",
        run_key="tile-test-one",
        acquire=lambda _: (tile_acquisition(png), "2021-v2"),
    )
    assert first["saved"] == 1
    saved, original = archived_tile(provider, 13, 5334, 3520)
    assert original == png and saved.capture.content_sha256 == hashlib.sha256(png).hexdigest()
    BasemapRequest.objects.update(last_attempt_at=timezone.now() - timedelta(hours=2))
    failure = archive_pending(
        provider,
        actor="test",
        run_key="tile-test-two",
        refresh=True,
        acquire=lambda _: (tile_acquisition(b"Source removed", 404), "2021-v2"),
    )
    assert failure["failed"] == 1 and Capture.objects.filter(http_status=404).exists()
    assert archived_tile(provider, 13, 5334, 3520)[1] == original
    with pytest.raises(ValueError):
        archived_tile("https://example.com", 13, 5334, 3520)
