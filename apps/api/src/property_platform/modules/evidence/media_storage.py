"""Archive verified evidence outside SQL transactions; publish only reviewed photographs."""

import io

from django.conf import settings
from django.db import connection, transaction
from django.db.models import F, Q
from django.utils import timezone

from property_platform.object_storage.adapters import LocalStore, S3Store, private_store
from property_platform.object_storage.core import (
    MIME_TYPES,
    ObjectReceipt,
    StorageConfig,
    StorageError,
    prepare_asset,
)

from .models import Capture, CaptureObject, MediaPublication, PropertyMedia, StoredObject


def storage_config():
    return StorageConfig(**settings.MEDIA_STORAGE).validate()


def eligible_media():
    return PropertyMedia.objects.filter(
        display_allowed=True,
        mime_type="image/jpeg",
        licence_code__in=["CC-BY-3.0", "CC-BY-4.0", "CC0-1.0"],
        capture__run__status="succeeded",
        capture__http_status=200,
        capture__parent_capture_id=F("licence_capture_id"),
        licence_capture__run__status="succeeded",
        licence_capture__http_status=200,
    )


def _actor(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 160:
        raise ValueError("Media actor must contain 1–160 characters")
    return value.strip()


def object_receipt(row):
    return ObjectReceipt(
        row.backend,
        row.namespace,
        row.bucket,
        row.object_key,
        row.content_sha256,
        row.byte_length,
        row.mime_type,
    ).validate()


def _record(receipt):
    row, _ = StoredObject.objects.get_or_create(
        namespace=receipt.namespace,
        bucket=receipt.bucket,
        object_key=receipt.key,
        defaults={
            "backend": receipt.backend,
            "content_sha256": receipt.sha256,
            "byte_length": receipt.size,
            "mime_type": receipt.mime_type,
            "verified_at": timezone.now(),
        },
    )
    if object_receipt(row) != receipt:
        raise StorageError("Object location conflicts with recorded metadata")
    return row


def archive_capture(capture, *, mime_type, actor, store=None):
    """Reusable for acquired PDF/video/GLB evidence; this does not authorize publication."""
    actor = _actor(actor)
    if connection.in_atomic_block:
        raise StorageError("Object writes must run outside SQL transactions")
    if capture.http_status != 200 or capture.run.status != "succeeded":
        raise StorageError("Only successful evidence can be archived")
    store = store or private_store(storage_config())
    with prepare_asset(io.BytesIO(bytes(capture.payload)), mime_type) as asset:
        if (asset.sha256, asset.size) != (capture.content_sha256, capture.byte_length):
            raise StorageError("Capture bytes do not match their provenance checksum")
        receipt = store.put(asset)
    # A crash before this commit leaves an unreferenced immutable object. Retrying reuses it.
    with transaction.atomic():
        current = Capture.objects.select_for_update().get(pk=capture.pk)
        if (current.content_sha256, current.byte_length) != (receipt.sha256, receipt.size):
            raise StorageError("Capture changed during archival")
        row = _record(receipt)
        CaptureObject.objects.get_or_create(
            capture=current, stored_object=row, defaults={"actor": actor}
        )
    return row


def read_capture(capture, *, max_bytes):
    """Legacy SQL payloads remain readable; a broken archived copy fails closed."""
    config = storage_config()
    namespace = "local" if config.backend == "local" else config.namespace
    copies = CaptureObject.objects.filter(capture_id=capture.id).select_related("stored_object")
    binding = (
        copies.filter(stored_object__namespace=namespace).order_by("-stored_at", "-id").first()
    )
    if binding is None:
        binding = copies.order_by("-stored_at", "-id").first()
    if binding is None:
        payload = bytes(capture.payload)
        import hashlib

        if (
            len(payload) > max_bytes
            or len(payload) != capture.byte_length
            or hashlib.sha256(payload).hexdigest() != capture.content_sha256
        ):
            raise StorageError("Capture bytes failed their integrity check")
        return payload
    receipt = object_receipt(binding.stored_object)
    if (receipt.sha256, receipt.size) != (capture.content_sha256, capture.byte_length):
        raise StorageError("Archived copy no longer matches its capture")
    store = LocalStore(config.local_root) if receipt.backend == "local" else S3Store(config)
    return store.read(receipt, max_bytes=max_bytes)


def publish_photo(media, *, actor, config=None):
    """An explicit operator action; no brochure, video or unreviewed URL is published."""
    actor = _actor(actor)
    if connection.in_atomic_block:
        raise StorageError("Object publication must run outside SQL transactions")
    config = config or storage_config()
    store = S3Store(config, public=True)
    if not eligible_media().filter(pk=media.pk).exists():
        raise StorageError("Media is not approved for public delivery")
    payload = read_capture(media.capture, max_bytes=2 * 1024 * 1024)
    with prepare_asset(io.BytesIO(payload), media.mime_type, max_bytes=2 * 1024 * 1024) as asset:
        receipt = store.put(
            asset, key=f"published/{media.id}/{asset.sha256}.{MIME_TYPES[asset.mime_type]}"
        )
    with transaction.atomic():
        # The public copy is exposed in the API only after this second rights check commits.
        PropertyMedia.objects.select_for_update().get(pk=media.pk)
        if not eligible_media().filter(pk=media.pk).exists():
            raise StorageError("Media approval changed during publication; remove the orphan copy")
        row = _record(receipt)
        publication, created = MediaPublication.objects.get_or_create(
            media=media, defaults={"stored_object": row, "actor": actor}
        )
        if not created and publication.stored_object_id != row.id:
            raise StorageError("A public location already exists; review before replacing it")
    return publication


def delivery_url(media):
    """No credentials or presigned private URLs enter the public read model."""
    config = storage_config()
    if not config.publication_enabled or not media.display_allowed:
        return None
    try:
        publication = media.mediapublication
    except MediaPublication.DoesNotExist:
        return None
    row = publication.stored_object
    receipt = object_receipt(row)
    if (
        (receipt.backend, receipt.namespace, receipt.bucket)
        != ("s3", config.namespace, config.public_bucket)
        or receipt.sha256 != media.capture.content_sha256
        or receipt.size != media.capture.byte_length
        or receipt.key != f"published/{media.id}/{receipt.sha256}.jpg"
    ):
        return None
    return f"{config.public_base_url.rstrip('/')}/{receipt.key}"


def archive_property_media(*, actor, limit=500, publish=False):
    """Bounded, resumable backfill. Source snapshots and legacy payloads are retained."""
    actor = _actor(actor)
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("Media batch limit must be 1–500")
    config = storage_config()
    store = private_store(config)
    if publish and not config.publication_enabled:
        raise StorageError("Explicit public storage opt-in is required")
    copied = CaptureObject.objects.filter(
        stored_object__namespace=store.namespace, stored_object__bucket=store.bucket
    ).values("capture_id")
    pending = Q(capture_id__in=copied)
    if publish:
        published = MediaPublication.objects.filter(
            stored_object__namespace=config.namespace, stored_object__bucket=config.public_bucket
        ).values("media_id")
        pending &= Q(pk__in=published)
    candidates = eligible_media().exclude(pending).select_related("capture__run").order_by("id")
    summary = {"archived": 0, "published": 0, "remaining": 0}
    for media in candidates[:limit].iterator(chunk_size=1):
        archive_capture(media.capture, mime_type=media.mime_type, actor=actor, store=store)
        summary["archived"] += 1
        if publish:
            publish_photo(media, actor=actor, config=config)
            summary["published"] += 1
    summary["remaining"] = candidates.count()
    return summary
