"""Second copy of finished backups (A30): a host folder today, S3-compatible storage later.

The owner keeps backups local for now (decision of 3 November 2026) and wants the copy to
move to the cloud later without a rewrite. `BACKUP_COPY_TARGET` picks the destination; empty
means no copy. A target only stores, lists and returns bytes: what is copied, in which order,
retention and verification live here, so a cloud destination is one class plus settings.
Credentials come from the environment, never from Git or an image.
"""

import base64
import json
import os
import shutil
from pathlib import Path

from . import backups

FILES = "files"
# Objects above this size need a multipart upload, which the S3 target does not do yet.
S3_SINGLE_PUT_LIMIT = 5 * 1024**3


class CopyError(RuntimeError):
    """A copy that could not be written or verified; the backup flow fails on it."""


class DirectoryTarget:
    """A host folder mounted into the runner: external disk, synced folder or network share."""

    kind = "directory"

    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        path = self.root.joinpath(*key.split("/"))
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise CopyError(f"Copy key {key} escapes the destination")
        return path

    def inventory(self, prefix: str) -> dict[str, int]:
        """Keys that start with `prefix`, with their sizes; partial copies are not listed."""
        base = self._path("/".join(prefix.split("/")[:-1]))
        found = {}
        for path in base.rglob("*") if base.is_dir() else ():
            key = path.relative_to(self.root).as_posix()
            if key.startswith(prefix) and path.is_file() and not path.name.endswith(".partial"):
                found[key] = path.stat().st_size
        return found

    def put(self, source: Path, key: str, sha256: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(f".{path.name}.partial")
        shutil.copyfile(source, partial)
        if partial.stat().st_size != source.stat().st_size or backups._sha256(partial) != sha256:
            partial.unlink(missing_ok=True)
            raise CopyError(f"Copy of {key} failed its size or SHA-256 check")
        partial.replace(path)

    def describe(self, key: str) -> tuple[int, str] | None:
        path = self._path(key)
        return (path.stat().st_size, backups._sha256(path)) if path.is_file() else None

    def fetch(self, key: str, destination: Path) -> None:
        shutil.copyfile(self._path(key), destination)

    def remove(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def local_root(self) -> Path | None:
        return self.root


class S3Target:
    """Any S3-compatible bucket. Not active anywhere: choosing a provider is the owner's call.

    Each object carries its SHA-256 as metadata and as the S3 integrity checksum, so the
    provider rejects a corrupted upload and a restore check can verify without downloading.
    """

    kind = "s3"

    def __init__(self, client, bucket: str, prefix: str = ""):
        self.client, self.bucket = client, bucket
        self.prefix = prefix.strip("/") + "/" if prefix.strip("/") else ""

    @classmethod
    def from_environment(cls) -> S3Target:
        import boto3

        required = ("ENDPOINT_URL", "BUCKET", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY")
        settings = {name: os.environ.get(f"BACKUP_COPY_S3_{name}", "") for name in required}
        if missing := [name for name, value in settings.items() if not value]:
            raise CopyError(f"BACKUP_COPY_S3_{', BACKUP_COPY_S3_'.join(missing)} not set")
        client = boto3.client(
            "s3",
            endpoint_url=settings["ENDPOINT_URL"],
            region_name=os.environ.get("BACKUP_COPY_S3_REGION") or "auto",
            aws_access_key_id=settings["ACCESS_KEY_ID"],
            aws_secret_access_key=settings["SECRET_ACCESS_KEY"],
        )
        return cls(client, settings["BUCKET"], os.environ.get("BACKUP_COPY_S3_PREFIX", ""))

    def inventory(self, prefix: str) -> dict[str, int]:
        found = {}
        pages = self.client.get_paginator("list_objects_v2").paginate(
            Bucket=self.bucket, Prefix=self.prefix + prefix
        )
        for page in pages:
            for item in page.get("Contents", []):
                found[item["Key"][len(self.prefix) :]] = item["Size"]
        return found

    def put(self, source: Path, key: str, sha256: str) -> None:
        size = source.stat().st_size
        if size > S3_SINGLE_PUT_LIMIT:
            raise CopyError(f"{key} needs a multipart upload ({size} bytes)")
        with source.open("rb") as body:
            self.client.put_object(
                Bucket=self.bucket,
                Key=self.prefix + key,
                Body=body,
                ContentLength=size,
                ChecksumSHA256=base64.b64encode(bytes.fromhex(sha256)).decode(),
                Metadata={"sha256": sha256},
            )
        if self.describe(key) != (size, sha256):
            raise CopyError(f"Copy of {key} failed its size or SHA-256 check")

    def describe(self, key: str) -> tuple[int, str | None] | None:
        from botocore.exceptions import ClientError

        try:
            head = self.client.head_object(Bucket=self.bucket, Key=self.prefix + key)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise
        return head["ContentLength"], head.get("Metadata", {}).get("sha256")

    def fetch(self, key: str, destination: Path) -> None:
        body = self.client.get_object(Bucket=self.bucket, Key=self.prefix + key)["Body"]
        with destination.open("wb") as handle:
            for chunk in iter(lambda: body.read(1024 * 1024), b""):
                handle.write(chunk)

    def remove(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self.prefix + key)

    def local_root(self) -> Path | None:
        return None


def copy_target():
    kind = os.environ.get("BACKUP_COPY_TARGET", "").strip()
    if not kind:
        return None
    if kind == "directory":
        root = Path(os.environ.get("BACKUP_COPY_DIR", "/backup-copy"))
        if not root.is_dir():
            raise CopyError(f"Backup copy folder {root} is not mounted")
        return DirectoryTarget(root)
    if kind == "s3":
        return S3Target.from_environment()
    raise CopyError(f"Unknown BACKUP_COPY_TARGET {kind!r}")


def copied_backups(target) -> list[tuple]:
    """Complete backups in the copy, newest first: a manifest is written after its dump."""
    keys = target.inventory("")
    names = [
        key.removesuffix(".json")
        for key in keys
        if "/" not in key and key.endswith(".json") and f"{key.removesuffix('.json')}.dump" in keys
    ]
    return sorted(backups.parse_names(names), reverse=True)


def copy_backup(name: str | None = None, root: Path | None = None, target=None) -> dict:
    """Copy one finished backup and the private file mirror, then apply retention.

    Order: mirror files, dump, manifest. A manifest in the copy therefore means its dump and
    the files it references are there too. Already copied files of the same size are
    skipped: mirrored objects are named by their SHA-256 and receipts are never rewritten.
    """
    root = root or backups.backup_root()
    target = target or copy_target()
    if target is None:
        return {"target": "none"}
    name = name or backups.backups(root)[0][1]
    manifest_path = root / f"{name}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    present = target.inventory(f"{FILES}/")
    copied = copied_bytes = 0
    mirror = root / FILES
    for path in sorted(mirror.rglob("*")) if mirror.is_dir() else ():
        if not path.is_file() or path.is_symlink():
            continue
        key = path.relative_to(root).as_posix()
        if present.get(key) != path.stat().st_size:
            target.put(path, key, backups._sha256(path))
            copied += 1
            copied_bytes += path.stat().st_size
    dump = root / manifest["dump"]
    dump_copied = target.inventory(dump.name).get(dump.name) != manifest["bytes"]
    if dump_copied:
        target.put(dump, dump.name, manifest["sha256"])
    target.put(manifest_path, manifest_path.name, backups._sha256(manifest_path))
    return {
        "target": target.kind,
        "name": name,
        "dump_copied": dump_copied,
        "files_copied": copied,
        "files_copied_bytes": copied_bytes,
        "pruned": prune_copy(target),
    }


def prune_copy(target) -> list[str]:
    """Same retention as the local folder; mirrored files are never deleted."""
    found = copied_backups(target)
    keep = backups.retained(found)
    removed = []
    for _, name in found:
        if name not in keep:
            target.remove(f"{name}.json")
            target.remove(f"{name}.dump")
            removed.append(name)
    return removed


def restore_check_from_copy(url: str | None = None, target=None) -> dict:
    """Restore the newest copied backup and check its objects against the copy itself."""
    target = target or copy_target()
    if target is None:
        raise CopyError("No backup copy is configured (BACKUP_COPY_TARGET)")
    local = target.local_root()
    if local is not None:
        return {"source": target.kind, **backups.restore_check(url, root=local)}
    found = copied_backups(target)
    if not found:
        raise FileNotFoundError("No complete backup in the copy")
    name = found[0][1]
    work = backups.backup_root() / ".copy-restore"
    work.mkdir(parents=True, exist_ok=True)
    try:
        for suffix in (".json", ".dump"):
            target.fetch(f"{name}{suffix}", work / f"{name}{suffix}")
        result = backups.restore_check(
            url,
            name=name,
            root=work,
            describe=lambda key: target.describe(f"{FILES}/media/{key}"),
        )
    finally:
        for suffix in (".json", ".dump"):
            (work / f"{name}{suffix}").unlink(missing_ok=True)
    return {"source": target.kind, **result}
