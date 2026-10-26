"""Move raw capture bodies out of PostgreSQL into private, content-addressed storage.

The SQL body is cleared only after a copy of the same SHA-256 and size has been written and
read back; the `protect_capture_bytes` trigger refuses any other removal. Readers go through
`read_capture`, which prefers the archived copy and fails closed when it is broken.
"""

import hashlib
import io

from django.db import connection, transaction
from django.db.models import Count, Sum

from property_platform.object_storage.adapters import private_store
from property_platform.object_storage.core import MAX_BYTES, StorageError, prepare_asset

from .media_storage import _actor, _record, object_receipt, storage_config
from .models import Capture, CaptureObject

RAW_MIME_TYPE = "application/octet-stream"
# Small bodies stay in SQL: they weigh little and one file per response would not pay off.
DEFAULT_MIN_BYTES = 64 * 1024


def inherited_body(parent):
    """A derived capture shares its parent's bytes wherever they live; nothing is re-read."""
    if parent.primary_object_id is not None:
        return {"payload": None, "primary_object_id": parent.primary_object_id}
    return {"payload": parent.payload, "primary_object_id": None}


def _verified_copy(capture, store):
    """Reuse an existing binding in this store (archived photographs) after reading it back."""
    binding = (
        CaptureObject.objects.filter(
            capture_id=capture.id,
            stored_object__namespace=store.namespace,
            stored_object__bucket=store.bucket,
            stored_object__content_sha256=capture.content_sha256,
            stored_object__byte_length=capture.byte_length,
        )
        .select_related("stored_object")
        .order_by("-stored_at", "-id")
        .first()
    )
    if binding is None:
        return None
    store.read(object_receipt(binding.stored_object), collect=False)
    return binding.stored_object


def relocate_capture(capture_id, *, actor, store):
    """Copy, verify, then clear one SQL body. Idempotent; a crash leaves the SQL body intact."""
    actor = _actor(actor)
    if connection.in_atomic_block:
        raise StorageError("Object writes must run outside SQL transactions")
    capture = Capture.objects.get(pk=capture_id)
    if capture.payload is None:
        return None
    stored = _verified_copy(capture, store)
    if stored is None:
        payload = bytes(capture.payload)
        if (
            len(payload) != capture.byte_length
            or hashlib.sha256(payload).hexdigest() != capture.content_sha256
        ):
            raise StorageError("Capture bytes failed their provenance checksum")
        with prepare_asset(io.BytesIO(payload), RAW_MIME_TYPE) as asset:
            # `put` reads the object back and checks its size and SHA-256 before returning.
            receipt = store.put(asset)
    with transaction.atomic():
        locked = (
            Capture.objects.select_for_update()
            .only("id", "content_sha256", "byte_length")
            .filter(pk=capture.pk, payload__isnull=False)
            .first()
        )
        if locked is None:
            return None
        if stored is None:
            stored = _record(receipt)
        if (stored.content_sha256, stored.byte_length) != (
            locked.content_sha256,
            locked.byte_length,
        ):
            raise StorageError("Capture changed during relocation")
        CaptureObject.objects.get_or_create(
            capture_id=locked.pk, stored_object=stored, defaults={"actor": actor}
        )
        # The trigger accepts a NULL body only with a verified copy of the same fingerprint.
        Capture.objects.filter(pk=locked.pk).update(payload=None, primary_object=stored)
    return stored


def _pending(min_bytes):
    return Capture.objects.filter(
        payload__isnull=False, byte_length__gte=min_bytes, byte_length__lte=MAX_BYTES
    )


def capture_body_report(*, min_bytes=DEFAULT_MIN_BYTES):
    """Where capture bodies live, without reading any of them."""
    totals = {}
    for label, queryset in (
        ("sql", Capture.objects.filter(payload__isnull=False)),
        ("sql_to_relocate", _pending(min_bytes)),
        ("object", Capture.objects.filter(payload__isnull=True)),
    ):
        row = queryset.aggregate(captures=Count("id"), bytes=Sum("byte_length"))
        totals[label] = {"captures": row["captures"], "bytes": row["bytes"] or 0}
    return {"min_bytes": min_bytes, **totals}


def relocate_capture_bodies(*, actor, limit=200, min_bytes=DEFAULT_MIN_BYTES):
    """Bounded, resumable batch, oldest first. Bodies below `min_bytes` stay in SQL."""
    actor = _actor(actor)
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Capture batch limit must be 1–1000")
    if type(min_bytes) is not int or not 1 <= min_bytes <= MAX_BYTES:
        raise ValueError("Minimum body size must be 1 byte to 128 MiB")
    store = private_store(storage_config())
    summary = {"relocated": 0, "relocated_bytes": 0}
    for capture_id in list(_pending(min_bytes).order_by("id").values_list("id", flat=True)[:limit]):
        stored = relocate_capture(capture_id, actor=actor, store=store)
        if stored is not None:
            summary["relocated"] += 1
            summary["relocated_bytes"] += stored.byte_length
    remaining = _pending(min_bytes).aggregate(captures=Count("id"), bytes=Sum("byte_length"))
    summary["remaining"] = remaining["captures"]
    summary["remaining_bytes"] = remaining["bytes"] or 0
    return summary
