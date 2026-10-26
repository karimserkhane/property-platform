"""Private, immutable objects. An object key is never a user-supplied path or URL."""

import hashlib
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlsplit

CHUNK = 1024 * 1024
MAX_BYTES = 128 * CHUNK
MIME_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "application/pdf": "pdf",
    "video/mp4": "mp4",
    "video/webm": "webm",
    "model/gltf-binary": "glb",
    # Raw source responses (JSON, HTML, protobuf, tiles): bytes only, never served or published.
    "application/octet-stream": "bin",
}


class StorageError(ValueError):
    """A safe diagnostic; provider responses and credentials never reach the client."""


@dataclass(frozen=True)
class StorageConfig:
    backend: str = "local"
    local_root: str = field(default_factory=lambda: str(Path.cwd() / ".cache" / "media"))
    namespace: str = "r2-primary"
    endpoint_url: str = ""
    region: str = "auto"
    bucket: str = ""
    access_key_id: str = field(default="", repr=False)
    secret_access_key: str = field(default="", repr=False)
    public_bucket: str = ""
    public_base_url: str = ""
    publication_enabled: bool = False

    def validate(self):
        if self.backend not in {"local", "s3"}:
            raise StorageError("Unsupported media storage backend")
        if not Path(self.local_root).is_absolute():
            raise StorageError("Media storage root must be absolute")
        if self.backend == "s3":
            validate_origin(self.endpoint_url)
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", self.namespace):
                raise StorageError("Invalid storage namespace")
            if self.namespace == "local" or not all(
                (self.bucket, self.region, self.access_key_id, self.secret_access_key)
            ):
                raise StorageError("Explicit S3 configuration and credentials are required")
            validate_bucket(self.bucket)
        if self.publication_enabled:
            if self.backend != "s3" or not self.public_bucket or self.public_bucket == self.bucket:
                raise StorageError("Publication requires a separate S3 public bucket")
            validate_bucket(self.public_bucket)
            validate_origin(self.public_base_url)
            if urlsplit(self.public_base_url).hostname.endswith(".r2.dev"):
                raise StorageError("Use a CDN custom domain, not an r2.dev development URL")
        return self


def validate_origin(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise StorageError("Storage URL must be a configured HTTPS origin")


def validate_bucket(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", value):
        raise StorageError("Invalid storage bucket")


def validate_key(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"(?:objects/sha256/[a-f0-9]{2}|published/[a-f0-9-]{36})/[a-f0-9]{64}\.(?:jpg|png|webp|pdf|mp4|webm|glb|bin)",
        value,
    ):
        raise StorageError("Invalid immutable object key")


@dataclass(frozen=True)
class ObjectReceipt:
    backend: str
    namespace: str
    bucket: str
    key: str
    sha256: str
    size: int
    mime_type: str

    def validate(self):
        validate_key(self.key)
        if (
            self.backend not in {"local", "s3"}
            or not re.fullmatch(r"[a-f0-9]{64}", self.sha256)
            or not 0 < self.size <= MAX_BYTES
            or self.mime_type not in MIME_TYPES
            or not self.key.endswith(f"/{self.sha256}.{MIME_TYPES[self.mime_type]}")
        ):
            raise StorageError("Invalid stored object metadata")
        return self


@dataclass
class PreparedAsset:
    stream: BinaryIO
    sha256: str
    size: int
    mime_type: str

    @property
    def key(self):
        return f"objects/sha256/{self.sha256[:2]}/{self.sha256}.{MIME_TYPES[self.mime_type]}"


def validate_magic(prefix, mime):
    valid = {
        "image/jpeg": prefix.startswith(b"\xff\xd8\xff"),
        "image/png": prefix.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP",
        "application/pdf": prefix.startswith(b"%PDF-"),
        "video/mp4": prefix[4:8] == b"ftyp",
        "video/webm": prefix.startswith(b"\x1aE\xdf\xa3"),
        "model/gltf-binary": prefix.startswith(b"glTF\x02\x00\x00\x00"),
        "application/octet-stream": True,
    }.get(mime, False)
    if not valid:
        raise StorageError("Content does not match the allowed media type")


@contextmanager
def prepare_asset(source: BinaryIO, mime_type: str, *, max_bytes=MAX_BYTES):
    """Freeze and hash bounded input; large inputs spill to a temporary file, not RAM."""
    if mime_type not in MIME_TYPES or not 1 <= max_bytes <= MAX_BYTES:
        raise StorageError("Unsupported media type or size budget")
    with tempfile.SpooledTemporaryFile(max_size=CHUNK, mode="w+b") as spool:
        digest, size, prefix = hashlib.sha256(), 0, b""
        while block := source.read(min(CHUNK, max_bytes - size + 1)):
            size += len(block)
            if size > max_bytes:
                raise StorageError("Media exceeds its byte budget")
            prefix = (prefix + block)[:64] if len(prefix) < 64 else prefix
            digest.update(block)
            spool.write(block)
        if not size:
            raise StorageError("Empty media is not allowed")
        validate_magic(prefix, mime_type)
        spool.seek(0)
        yield PreparedAsset(spool, digest.hexdigest(), size, mime_type)


def checked_body(stream, receipt, *, max_bytes=MAX_BYTES, collect=True):
    receipt.validate()
    if receipt.size > max_bytes:
        raise StorageError("Stored object exceeds its read budget")
    digest, size, blocks = hashlib.sha256(), 0, []
    while block := stream.read(min(CHUNK, max_bytes - size + 1)):
        size += len(block)
        if size > max_bytes:
            raise StorageError("Stored object exceeds its read budget")
        digest.update(block)
        if collect:
            blocks.append(block)
    if size != receipt.size or digest.hexdigest() != receipt.sha256:
        raise StorageError("Stored object failed its integrity check")
    return b"".join(blocks) if collect else None
