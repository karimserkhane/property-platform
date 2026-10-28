"""Bounded single-range downloads for approved media; no arbitrary URLs or multipart ranges."""

import hashlib
import os
import re
import time
from dataclasses import dataclass
from functools import lru_cache

from .core import CHUNK, ObjectReceipt, StorageError, checked_body


class UnsatisfiableRange(ValueError):
    pass


@dataclass(frozen=True)
class DownloadRange:
    start: int
    end: int
    partial: bool = False

    @property
    def size(self):
        return self.end - self.start + 1


def download_range(value, size):
    if not value:
        return DownloadRange(0, size - 1)
    if len(value) > 80 or not (match := re.fullmatch(r"bytes=(\d*)-(\d*)", value)):
        raise UnsatisfiableRange("Only a single byte range is supported")
    first, last = match.groups()
    if not first:
        if not last or int(last) == 0:
            raise UnsatisfiableRange("Invalid suffix range")
        return DownloadRange(max(0, size - int(last)), size - 1, True)
    start, end = int(first), min(int(last), size - 1) if last else size - 1
    if start >= size or end < start:
        raise UnsatisfiableRange("Range is outside the object")
    return DownloadRange(start, end, True)


def _fingerprint(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _verify_local_uncached(path, fingerprint, receipt):
    # Trusted owner-only immutable volume. Any filesystem change invalidates this cache.
    with open(path, "rb") as handle:
        if _fingerprint(os.fstat(handle.fileno())) != fingerprint:
            raise StorageError("Local media changed before verification")
        checked_body(handle, receipt, collect=False)
        if _fingerprint(os.fstat(handle.fileno())) != fingerprint:
            raise StorageError("Local media changed during verification")


_cached_verify = lru_cache(maxsize=256)(_verify_local_uncached)


def _verify_local(path, fingerprint, receipt):
    # Docker filesystems may give two rapid writes the same timestamp. Do not
    # cache freshly written files; old immutable objects can reuse verification.
    if max(fingerprint[-2:]) >= time.time_ns() - 2_000_000_000:
        return _verify_local_uncached(path, fingerprint, receipt)
    return _cached_verify(path, fingerprint, receipt)


def _location(store, receipt):
    receipt.validate()
    if (receipt.backend, receipt.namespace, receipt.bucket) != (
        store.backend,
        store.namespace,
        store.bucket,
    ):
        raise StorageError("Media belongs to another storage location")


def describe_object(store, receipt):
    """Verify availability without returning the body. Provider errors stay private."""
    _location(store, receipt)
    if store.backend == "local":
        try:
            path = store._path(receipt.key)
            _verify_local(str(path), _fingerprint(path.stat()), receipt)
            return
        except OSError:
            raise StorageError("Local media is unavailable") from None
    from botocore.exceptions import BotoCoreError, ClientError

    try:
        result = store.client.head_object(Bucket=store.bucket, Key=receipt.key)
        _check_s3_metadata(result, receipt, receipt.size)
    except BotoCoreError, ClientError, OSError:
        raise StorageError("S3 media is unavailable") from None


def _check_s3_metadata(result, receipt, length):
    if (
        result.get("ContentLength") != length
        or result.get("ContentType") != receipt.mime_type
        or result.get("Metadata", {}).get("sha256") != receipt.sha256
    ):
        raise StorageError("Media metadata failed its integrity check")


class ObjectDownload:
    """Owns an open file/socket. The HTTP response must register close() on disconnect."""

    def __init__(self, handle, receipt, span, *, full_hash=False):
        self.handle, self.receipt, self.span, self.full_hash = handle, receipt, span, full_hash

    def __iter__(self):
        remaining, digest = self.span.size, hashlib.sha256()
        try:
            while remaining:
                block = self.handle.read(min(CHUNK // 16, remaining))
                if not block:
                    raise StorageError("Media stream ended before its expected length")
                if len(block) > remaining:
                    raise StorageError("Media stream exceeded its read budget")
                remaining -= len(block)
                if self.full_hash:
                    digest.update(block)
                yield block
            if self.full_hash and digest.hexdigest() != self.receipt.sha256:
                raise StorageError("Media stream failed its integrity check")
        finally:
            self.close()

    def close(self):
        self.handle.close()


def open_object(store, receipt: ObjectReceipt, span: DownloadRange):
    _location(store, receipt)
    if not 0 <= span.start <= span.end < receipt.size:
        raise UnsatisfiableRange("Range is outside the object")
    if store.backend == "local":
        handle = None
        try:
            path = store._path(receipt.key)
            handle = path.open("rb")
            _verify_local(str(path), _fingerprint(os.fstat(handle.fileno())), receipt)
            handle.seek(span.start)
            return ObjectDownload(handle, receipt, span)
        except OSError, StorageError:
            if handle is not None:
                handle.close()
            raise StorageError("Local media is unavailable or invalid") from None
    from botocore.exceptions import BotoCoreError, ClientError

    body = None
    try:
        params = {"Bucket": store.bucket, "Key": receipt.key}
        if span.partial:
            params["Range"] = f"bytes={span.start}-{span.end}"
        result = store.client.get_object(**params)
        body = result["Body"]
        _check_s3_metadata(result, receipt, span.size)
        if span.partial and result.get("ContentRange") != (
            f"bytes {span.start}-{span.end}/{receipt.size}"
        ):
            raise StorageError("S3 returned a different byte range")
        return ObjectDownload(body, receipt, span, full_hash=not span.partial)
    except BotoCoreError, ClientError, OSError, StorageError:
        if body is not None:
            body.close()
        raise StorageError("S3 media stream is unavailable or invalid") from None
