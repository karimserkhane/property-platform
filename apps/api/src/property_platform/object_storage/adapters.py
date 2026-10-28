"""Filesystem and S3 implementations. No cloud resources are created implicitly."""

import os
import shutil
import tempfile
from pathlib import Path

from .core import ObjectReceipt, StorageError, checked_body, validate_key


class LocalStore:
    namespace = "local"
    bucket = ""
    backend = "local"

    def __init__(self, root):
        self.root = Path(root).resolve()

    def _path(self, key):
        validate_key(key)
        path = self.root.joinpath(*key.split("/"))
        # The root is a trusted operator-controlled volume, never an upload directory.
        if any(parent.is_symlink() for parent in (path, *path.parents) if parent != self.root):
            raise StorageError("Symbolic links are forbidden in media storage")
        if not path.resolve().is_relative_to(self.root):
            raise StorageError("Object escapes its storage root")
        return path

    def put(self, asset, *, key=None):
        key = key or asset.key
        receipt = ObjectReceipt(
            self.backend,
            self.namespace,
            self.bucket,
            key,
            asset.sha256,
            asset.size,
            asset.mime_type,
        ).validate()
        path = self._path(key)
        temporary = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as target:
                temporary = Path(target.name)
                asset.stream.seek(0)
                shutil.copyfileobj(asset.stream, target, length=1024 * 1024)
                target.flush()
                os.fsync(target.fileno())
            # Atomic no-replace publication: a partial file is never visible at the final key.
            try:
                os.link(temporary, path)
            except FileExistsError:
                pass
            self.read(receipt, collect=False)
        except OSError:
            raise StorageError("Local media storage is unavailable") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return receipt

    def read(self, receipt, *, max_bytes=128 * 1024 * 1024, collect=True):
        if (receipt.backend, receipt.namespace, receipt.bucket) != ("local", "local", ""):
            raise StorageError("Object belongs to another storage location")
        try:
            with self._path(receipt.key).open("rb") as stream:
                return checked_body(stream, receipt, max_bytes=max_bytes, collect=collect)
        except OSError:
            raise StorageError("Local media object is unavailable") from None


class S3Store:
    backend = "s3"

    def __init__(self, config, *, public=False, client=None):
        config.validate()
        if config.backend != "s3" or (public and not config.publication_enabled):
            raise StorageError("S3 publication is not configured")
        self.namespace = config.namespace
        self.bucket = config.public_bucket if public else config.bucket
        if client is None:
            import boto3
            from botocore.config import Config

            client = boto3.client(
                "s3",
                endpoint_url=config.endpoint_url.rstrip("/"),
                region_name=config.region,
                aws_access_key_id=config.access_key_id,
                aws_secret_access_key=config.secret_access_key,
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"},
                    connect_timeout=5,
                    read_timeout=30,
                    retries={"mode": "standard", "total_max_attempts": 3},
                    request_checksum_calculation="when_required",
                    response_checksum_validation="when_required",
                ),
            )
        self.client = client
        self.public = public

    def put(self, asset, *, key=None):
        from botocore.exceptions import BotoCoreError, ClientError

        key = key or asset.key
        receipt = ObjectReceipt(
            self.backend,
            self.namespace,
            self.bucket,
            key,
            asset.sha256,
            asset.size,
            asset.mime_type,
        ).validate()
        asset.stream.seek(0)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=asset.stream,
                ContentLength=asset.size,
                ContentType=asset.mime_type,
                Metadata={"sha256": asset.sha256},
                IfNoneMatch="*",
                CacheControl="public, max-age=86400" if self.public else "private, no-store",
            )
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") not in (409, 412):
                raise StorageError("S3 media write failed") from None
            # A retry may find a prior successful write; an ETag is NOT a SHA-256 checksum.
            self.read(receipt, collect=False)
        except BotoCoreError:
            raise StorageError("S3 media write failed") from None
        return receipt

    def read(self, receipt, *, max_bytes=128 * 1024 * 1024, collect=True):
        from botocore.exceptions import BotoCoreError, ClientError

        receipt.validate()
        if (receipt.backend, receipt.namespace, receipt.bucket) != (
            self.backend,
            self.namespace,
            self.bucket,
        ):
            raise StorageError("Object belongs to another S3 storage location")
        if receipt.size > max_bytes:
            raise StorageError("Stored object exceeds its read budget")
        stream = None
        try:
            result = self.client.get_object(Bucket=self.bucket, Key=receipt.key)
            stream = result["Body"]
            if (
                result.get("ContentLength") != receipt.size
                or result.get("ContentType") != receipt.mime_type
                or result.get("Metadata", {}).get("sha256") != receipt.sha256
            ):
                raise StorageError("S3 object metadata failed its integrity check")
            return checked_body(stream, receipt, max_bytes=max_bytes, collect=collect)
        except BotoCoreError, ClientError, OSError:
            raise StorageError("S3 media read failed") from None
        finally:
            if stream is not None:
                stream.close()


def private_store(config):
    config.validate()
    return LocalStore(config.local_root) if config.backend == "local" else S3Store(config)
