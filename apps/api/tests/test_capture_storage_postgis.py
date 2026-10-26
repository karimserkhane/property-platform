import hashlib
import os
from unittest.mock import patch

import pytest
from django.db import DatabaseError, connection, transaction
from django.test import override_settings
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Capture relocation requires real PostGIS triggers", allow_module_level=True)

from property_platform.modules.evidence.capture_storage import (  # noqa: E402
    capture_body_report,
    inherited_body,
    relocate_capture,
    relocate_capture_bodies,
)
from property_platform.modules.evidence.media_storage import read_capture  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    CaptureObject,
    IngestionRun,
    RowRevision,
    Source,
    StoredObject,
)
from property_platform.object_storage.adapters import LocalStore  # noqa: E402
from property_platform.object_storage.core import StorageError  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

BIG = b'{"features": [' + b'{"id": 1},' * 8000 + b'{"id": 2}]}'


def capture(payload, url="https://example.com/source.json"):
    source, _ = Source.objects.get_or_create(
        key="test:raw", defaults={"name": "Test", "url": "https://example.com/"}
    )
    run = IngestionRun.objects.create(source=source, actor="test", connector_version="test")
    run.status, run.finished_at = "succeeded", timezone.now()
    run.save(update_fields=["status", "finished_at"])
    return Capture.objects.create(
        run=run,
        url=url,
        payload=payload,
        byte_length=len(payload),
        content_sha256=hashlib.sha256(payload).hexdigest(),
        http_status=200,
        fetched_at=timezone.now(),
    )


def test_bodies_move_after_a_verified_copy_and_read_back_identically(tmp_path):
    large, duplicate, small = capture(BIG), capture(BIG, "https://example.com/b"), capture(b"{}")
    stored_row = Capture.objects.get(pk=large.pk)
    dates = stored_row.fetched_at, stored_row.ingested_at
    with override_settings(MEDIA_STORAGE={"local_root": str(tmp_path)}):
        before = capture_body_report()
        assert before["sql_to_relocate"] == {"captures": 2, "bytes": 2 * len(BIG)}
        assert relocate_capture_bodies(actor="test", limit=1) == {
            "relocated": 1,
            "relocated_bytes": len(BIG),
            "remaining": 1,
            "remaining_bytes": len(BIG),
        }
        assert relocate_capture_bodies(actor="retry")["relocated"] == 1
        assert relocate_capture_bodies(actor="retry")["relocated"] == 0
        # Identical bytes share one immutable object; each capture keeps its own binding.
        assert StoredObject.objects.get().mime_type == "application/octet-stream"
        assert CaptureObject.objects.count() == 2
        for row in (large, duplicate):
            row = Capture.objects.get(pk=row.pk)
            assert row.payload is None and row.primary_object_id is not None
            assert read_capture(row, max_bytes=len(BIG)) == BIG
        relocated = Capture.objects.get(pk=large.pk)
        assert (relocated.fetched_at, relocated.ingested_at) == dates
        # Small bodies stay in SQL by default.
        assert bytes(Capture.objects.get(pk=small.pk).payload) == b"{}"
        assert capture_body_report()["object"] == {"captures": 2, "bytes": 2 * len(BIG)}
        key = StoredObject.objects.get().object_key
        assert (tmp_path / key).read_bytes() == BIG
    revisions = RowRevision.objects.filter(table_name="capture", row_key=str(large.pk))
    assert revisions.filter(operation="UPDATE").count() == 1


def test_storage_failure_keeps_the_sql_body_and_a_retry_completes(tmp_path):
    row = capture(BIG)
    store = LocalStore(tmp_path)
    with patch.object(LocalStore, "put", side_effect=StorageError("disk full")):
        with pytest.raises(StorageError):
            relocate_capture(row.pk, actor="test", store=store)
    row.refresh_from_db()
    assert bytes(row.payload) == BIG and StoredObject.objects.count() == 0
    with override_settings(MEDIA_STORAGE={"local_root": str(tmp_path)}):
        assert relocate_capture(row.pk, actor="test", store=store) is not None
        assert relocate_capture(row.pk, actor="test", store=store) is None


def test_no_storage_io_inside_a_transaction_and_no_unverified_removal(tmp_path):
    row = capture(BIG)
    with transaction.atomic(), pytest.raises(StorageError):
        relocate_capture(row.pk, actor="test", store=LocalStore(tmp_path))
    other = StoredObject.objects.create(
        backend="local",
        namespace="local",
        object_key=f"objects/sha256/00/{'0' * 64}.bin",
        content_sha256="0" * 64,
        byte_length=len(BIG),
        mime_type="application/octet-stream",
        verified_at=timezone.now(),
    )
    with pytest.raises(DatabaseError, match="verified copy"), transaction.atomic():
        Capture.objects.filter(pk=row.pk).update(payload=None, primary_object=other)
    row.refresh_from_db()
    assert bytes(row.payload) == BIG


def test_a_corrupt_copy_fails_closed_and_derived_captures_share_the_object(tmp_path):
    row = capture(BIG)
    with override_settings(MEDIA_STORAGE={"local_root": str(tmp_path)}):
        stored = relocate_capture(row.pk, actor="test", store=LocalStore(tmp_path))
        row.refresh_from_db()
        derived = Capture.objects.create(
            run=row.run,
            parent_capture=row,
            url=row.url,
            **inherited_body(row),
            byte_length=row.byte_length,
            content_sha256=row.content_sha256,
            http_status=200,
            fetched_at=row.fetched_at,
            acquisition_method="stored_capture_reprocess",
        )
        assert derived.primary_object_id == stored.id
        assert read_capture(derived, max_bytes=len(BIG)) == BIG
        path = tmp_path / stored.object_key
        path.chmod(0o644)
        path.write_bytes(BIG[:-1] + b"!")
        with pytest.raises(StorageError):
            read_capture(row, max_bytes=len(BIG))
    with connection.cursor() as cursor:
        cursor.execute("SELECT payload IS NULL FROM evidence.capture WHERE id=%s", [row.pk])
        assert cursor.fetchone() == (True,)
