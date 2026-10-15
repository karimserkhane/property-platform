import hashlib
import os
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Media provenance requires real PostGIS", allow_module_level=True)

from django.db import connection, transaction  # noqa: E402
from test_property_presentations_postgis import sample  # noqa: E402

from property_platform.modules.evidence.media_storage import (  # noqa: E402
    archive_capture,
    archive_property_media,
    delivery_url,
    publish_photo,
)
from property_platform.modules.evidence.models import (  # noqa: E402
    CaptureObject,
    MediaPublication,
    PropertyMedia,
    StoredObject,
)
from property_platform.modules.evidence.property_import import import_presentations  # noqa: E402
from property_platform.modules.evidence.queries import property_media_asset  # noqa: E402
from property_platform.object_storage.adapters import LocalStore  # noqa: E402
from property_platform.object_storage.core import ObjectReceipt, StorageError  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def imported(times=1):
    _, row, photo, receipts = sample()
    for _ in range(times):
        import_presentations(receipts, actor="reviewer", profiles=[row], photos={"example": photo})
    return PropertyMedia.objects.select_related("capture__run").order_by("id")


def test_archive_deduplicates_bytes_preserves_captures_and_resumes_batches(tmp_path):
    photos = list(imported(2))
    original_dates = [(p.capture.fetched_at, p.capture.ingested_at) for p in photos]
    with override_settings(MEDIA_STORAGE={"local_root": str(tmp_path)}):
        assert archive_property_media(actor="first", limit=1) == {
            "archived": 1,
            "published": 0,
            "remaining": 1,
        }
        assert archive_property_media(actor="retry")["archived"] == 1
        assert archive_property_media(actor="retry")["archived"] == 0
        assert StoredObject.objects.count() == 1
        assert CaptureObject.objects.count() == 2
        for photo, dates in zip(photos, original_dates, strict=True):
            photo.capture.refresh_from_db()
            assert (photo.capture.fetched_at, photo.capture.ingested_at) == dates
            with CaptureQueriesContext(connection) as reads:
                payload, _ = property_media_asset(photo.id)
            assert bytes(photo.capture.payload) == payload
            assert all('"payload"' not in query["sql"] for query in reads)
            assert delivery_url(photo) is None
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_name IN ('stored_object','capture_object','media_publication')"
        )
        assert set(cursor.fetchall()) == {
            ("evidence", "stored_object"),
            ("evidence", "capture_object"),
            ("evidence", "media_publication"),
        }


def test_corrupt_archived_object_does_not_silently_fall_back_to_sql(tmp_path, client):
    photo = imported().first()
    with override_settings(
        MEDIA_STORAGE={"local_root": str(tmp_path)},
        DEBUG=True,
        PROPERTY_PLATFORM_PARCEL_PREVIEW=True,
    ):
        archive_property_media(actor="test")
        obj = StoredObject.objects.get()
        tmp_path.joinpath(obj.object_key).write_bytes(b"wrong")
        assert client.get(f"/api/v1/preview/property-media/{photo.id}").status_code == 503
        assert bytes(photo.capture.payload).startswith(b"\xff\xd8\xff")


def test_failed_storage_and_interrupted_sql_can_be_retried_without_duplicate_bindings(tmp_path):
    photo = imported().first()
    with override_settings(MEDIA_STORAGE={"local_root": str(tmp_path)}):
        with patch.object(LocalStore, "put", side_effect=StorageError("offline")):
            with pytest.raises(StorageError):
                archive_property_media(actor="test")
        assert StoredObject.objects.count() == CaptureObject.objects.count() == 0
        with patch.object(
            CaptureObject.objects, "get_or_create", side_effect=RuntimeError("crash")
        ):
            with pytest.raises(RuntimeError):
                archive_property_media(actor="test")
        assert StoredObject.objects.count() == CaptureObject.objects.count() == 0
        assert list(
            tmp_path.rglob("*.jpg")
        )  # Unreferenced immutable file survives the SQL rollback.
        archive_property_media(actor="retry")
        assert StoredObject.objects.count() == CaptureObject.objects.count() == 1
        assert property_media_asset(photo.id)[0] == bytes(photo.capture.payload)


def test_no_cloud_io_inside_a_sql_transaction_and_no_checksum_forgery(tmp_path):
    photo = imported().first()
    with override_settings(MEDIA_STORAGE={"local_root": str(tmp_path)}):
        with transaction.atomic(), pytest.raises(StorageError, match="outside SQL"):
            archive_capture(photo.capture, mime_type=photo.mime_type, actor="test")
        photo.capture.content_sha256 = "0" * 64
        with pytest.raises(StorageError, match="provenance checksum"):
            archive_capture(photo.capture, mime_type=photo.mime_type, actor="test")
    assert not list(tmp_path.rglob("*.jpg"))


def test_only_an_explicit_approved_public_copy_exposes_a_cdn_url(tmp_path):
    photo = imported().first()
    config = {
        "backend": "s3",
        "local_root": str(tmp_path),
        "endpoint_url": "https://account.r2.cloudflarestorage.com",
        "bucket": "private-originals",
        "access_key_id": "key",
        "secret_access_key": "secret",
        "public_bucket": "public-media",
        "public_base_url": "https://media.example.com",
        "publication_enabled": True,
    }
    payload = bytes(photo.capture.payload)
    key = f"published/{photo.id}/{hashlib.sha256(payload).hexdigest()}.jpg"
    receipt = ObjectReceipt(
        "s3",
        "r2-primary",
        "public-media",
        key,
        hashlib.sha256(payload).hexdigest(),
        len(payload),
        "image/jpeg",
    )
    with override_settings(MEDIA_STORAGE={"local_root": str(tmp_path)}):
        with pytest.raises(StorageError, match="opt-in"):
            archive_property_media(actor="test", publish=True)
    with override_settings(MEDIA_STORAGE=config):
        assert delivery_url(photo) is None
        with patch("property_platform.modules.evidence.media_storage.S3Store") as adapter:
            adapter.return_value.put.return_value = receipt
            publish_photo(photo, actor="publisher")
        photo = PropertyMedia.objects.select_related(
            "capture", "mediapublication__stored_object"
        ).get(pk=photo.pk)
        assert delivery_url(photo) == f"https://media.example.com/{key}"
        photo.display_allowed = False
        photo.save(update_fields=["display_allowed"])
        assert delivery_url(photo) is None
        with pytest.raises(StorageError, match="not approved"):
            publish_photo(photo, actor="publisher")
    assert MediaPublication.objects.count() == 1
