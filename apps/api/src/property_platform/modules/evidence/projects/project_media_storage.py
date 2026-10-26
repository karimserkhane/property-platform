"""Private operator-supplied project files and explicit, audited delivery approval."""

from datetime import UTC, datetime
from pathlib import Path

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from property_platform.object_storage.adapters import S3Store, private_store
from property_platform.object_storage.core import MIME_TYPES, StorageError, prepare_asset
from property_platform.object_storage.downloads import download_range, open_object

from ..media_storage import (
    _actor,
    _record,
    capture_object_receipt,
    object_receipt,
    receipt_store,
    storage_config,
)
from ..models import (
    Capture,
    CaptureObject,
    IngestionRun,
    ProjectMedia,
    ProjectMediaPublication,
    Source,
)
from .property_protocol import safe_url


def _successful_capture(prefix):
    return Q(**{f"{prefix}__run__status": "succeeded"}) & (
        Q(**{f"{prefix}__http_status": 200})
        | Q(
            **{
                f"{prefix}__http_status__isnull": True,
                f"{prefix}__acquisition_method": "manual_media_file",
            }
        )
    )


def approved_media():
    return ProjectMedia.objects.filter(
        _successful_capture("asset_capture") & _successful_capture("rights_capture"),
        rights_status="approved",
        approved_at__isnull=False,
        approved_by__regex=r"\S",
        mime_type__in=list(MIME_TYPES),
        snapshot__capture__run__status="succeeded",
        snapshot__capture__http_status=200,
    )


def authorized_asset(identity):
    media = (
        approved_media()
        .select_related("asset_capture__primary_object")
        .defer("asset_capture__payload")
        .filter(pk=identity)
        .first()
    )
    if media is None:
        return None
    receipt = capture_object_receipt(media.asset_capture)
    if receipt is None or receipt.mime_type != media.mime_type:
        raise StorageError("Approved project file is not archived with matching metadata")
    return media, receipt


def attach_project_media_file(identity, path, *, actor):
    """An explicitly supplied local file, not a claim of an HTTP download or reuse rights."""
    actor = _actor(actor)
    if connection.in_atomic_block:
        raise StorageError("File intake must run outside SQL transactions")
    media = ProjectMedia.objects.select_related("asset_capture").get(pk=identity)
    if media.rights_status != "reference_only" or media.mime_type not in MIME_TYPES:
        raise StorageError("File intake requires an unapproved binary media reference")
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise StorageError("An ordinary operator-supplied media file is required")
    acquired_at = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    if acquired_at > timezone.now():
        raise StorageError("File timestamp is in the future")
    store = private_store(storage_config())
    with path.open("rb") as source, prepare_asset(source, media.mime_type) as asset:
        if media.asset_capture_id:
            if (media.asset_capture.content_sha256, media.asset_capture.byte_length) != (
                asset.sha256,
                asset.size,
            ):
                raise StorageError("Media already has another file; create a new reviewed revision")
            return media.asset_capture
        receipt = store.put(asset)
    with transaction.atomic():
        media = ProjectMedia.objects.select_for_update().get(pk=identity)
        if media.rights_status != "reference_only":
            raise StorageError("Media review changed during intake")
        if media.asset_capture_id:
            if media.asset_capture.content_sha256 != receipt.sha256:
                raise StorageError("Concurrent intake attached a different file")
            return media.asset_capture
        stored = _record(receipt)
        source, _ = Source.objects.get_or_create(
            key=f"project-file:{media.id}",
            defaults={"name": "Operator-supplied project media", "url": media.source_url},
        )
        run = IngestionRun.objects.create(
            source=source,
            actor=actor,
            connector_version="project-media-file-v1",
            status="running",
            summary={"media_id": str(media.id), "body_storage": "object"},
        )
        capture = Capture.objects.create(
            run=run,
            parent_capture=media.snapshot.capture,
            url=media.source_url,
            fetched_at=acquired_at,
            http_status=None,
            payload=None,
            primary_object=stored,
            content_sha256=receipt.sha256,
            byte_length=receipt.size,
            acquisition_method="manual_media_file",
            timestamp_basis="artifact_filesystem_time",
        )
        CaptureObject.objects.create(capture=capture, stored_object=stored, actor=actor)
        run.status, run.finished_at = "succeeded", timezone.now()
        run.save(update_fields=["status", "finished_at"])
        media.asset_capture = capture
        media.save(update_fields=["asset_capture"])
    return capture


def approve_project_media(identity, *, rights_capture_id, actor, author, licence_code, licence_url):
    """Trusted operator review of an existing proof. Never called automatically by collectors."""
    actor = _actor(actor)
    if (
        not isinstance(author, str)
        or not 1 <= len(author.strip()) <= 255
        or licence_code not in {"CC-BY-3.0", "CC-BY-4.0", "CC0-1.0", "explicit_permission"}
        or not safe_url(licence_url)
    ):
        raise StorageError("Approval requires author, a reviewed licence and its HTTPS reference")
    with transaction.atomic():
        media = (
            ProjectMedia.objects.select_for_update(of=("self",))
            .select_related("asset_capture")
            .get(pk=identity)
        )
        if media.rights_status != "reference_only" or not media.asset_capture_id:
            raise StorageError("Review requires an attached, unapproved file")
        if media.mime_type not in MIME_TYPES:
            raise StorageError("An external video webpage cannot be approved as a binary file")
        proof = Capture.objects.filter(
            Q(http_status=200)
            | Q(http_status__isnull=True, acquisition_method="manual_media_file"),
            pk=rights_capture_id,
            run__status="succeeded",
        ).first()
        if (
            proof is None
            or proof.id == media.asset_capture_id
            or proof.id == media.snapshot.terms_capture_id
        ):
            raise StorageError(
                "A separate successful rights grant is required; source terms are not a grant"
            )
        media.rights_capture = proof
        media.rights_status, media.approved_by, media.approved_at = (
            "approved",
            actor,
            timezone.now(),
        )
        media.author, media.licence_code, media.licence_url = (
            author.strip(),
            licence_code,
            licence_url,
        )
        media.save(
            update_fields=[
                "rights_capture",
                "rights_status",
                "approved_by",
                "approved_at",
                "author",
                "licence_code",
                "licence_url",
            ]
        )
    return media


def delivery_url(media):
    config = storage_config()
    if (
        media.rights_status != "approved"
        or not media.asset_capture_id
        or not media.rights_capture_id
    ):
        return None
    for capture in (media.asset_capture, media.rights_capture):
        if capture.run.status != "succeeded" or not (
            capture.http_status == 200
            or (capture.http_status is None and capture.acquisition_method == "manual_media_file")
        ):
            return None
    private_url = f"/api/atlas/project-media/{media.id}"
    if not config.publication_enabled:
        return private_url
    try:
        publication = media.projectmediapublication
    except ProjectMediaPublication.DoesNotExist:
        return private_url
    receipt = object_receipt(publication.stored_object)
    capture = media.asset_capture
    if (
        capture is None
        or media.mime_type not in MIME_TYPES
        or (receipt.backend, receipt.namespace, receipt.bucket)
        != ("s3", config.namespace, config.public_bucket)
        or (receipt.sha256, receipt.size, receipt.mime_type)
        != (capture.content_sha256, capture.byte_length, media.mime_type)
        or receipt.key != f"published/{media.id}/{receipt.sha256}.{MIME_TYPES[media.mime_type]}"
    ):
        return None
    return f"{config.public_base_url.rstrip('/')}/{receipt.key}"


def publish_project_media(identity, *, actor):
    actor = _actor(actor)
    if connection.in_atomic_block:
        raise StorageError("Media publication must run outside SQL transactions")
    config = storage_config()
    public = S3Store(config, public=True)
    asset = authorized_asset(identity)
    if asset is None:
        raise StorageError("Project media is not approved for delivery")
    media, receipt = asset
    download = open_object(receipt_store(receipt), receipt, download_range(None, receipt.size))
    try:
        with prepare_asset(download.handle, receipt.mime_type) as prepared:
            if (prepared.sha256, prepared.size) != (receipt.sha256, receipt.size):
                raise StorageError("Project file failed its publication integrity check")
            uploaded = public.put(
                prepared,
                key=f"published/{media.id}/{receipt.sha256}.{MIME_TYPES[media.mime_type]}",
            )
    finally:
        download.close()
    with transaction.atomic():
        ProjectMedia.objects.select_for_update().get(pk=identity)
        if not approved_media().filter(pk=identity).exists():
            raise StorageError("Approval changed; remove the unreferenced public copy")
        publication, _ = ProjectMediaPublication.objects.get_or_create(
            media=media, defaults={"stored_object": _record(uploaded), "actor": actor}
        )
        if object_receipt(publication.stored_object) != uploaded:
            raise StorageError(
                "Public location changed; a reviewed publication revision is required"
            )
    return publication
