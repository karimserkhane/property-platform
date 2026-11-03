"""Second copy of backups (A30): folder and S3 targets, order, retention and restore source."""

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import boto3
import pytest
from botocore.stub import ANY, Stubber

from property_platform_ingestion import backup_copy, backups

NAME = "property_platform-20261103T213000Z"


def make_backup(root: Path, name: str = NAME, dump: bytes = b"PGDMP-fake") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.dump").write_bytes(dump)
    (root / f"{name}.json").write_text(
        json.dumps({"dump": f"{name}.dump", "bytes": len(dump), "sha256": sha256(dump).hexdigest()})
    )


def test_copy_writes_files_then_dump_then_manifest_and_skips_what_is_there(tmp_path):
    root, copy = tmp_path / "backups", tmp_path / "copy"
    make_backup(root)
    (root / "files" / "media" / "objects").mkdir(parents=True)
    (root / "files" / "media" / "objects" / "a.bin").write_bytes(b"object")
    (root / "files" / "receipts").mkdir(parents=True)
    (root / "files" / "receipts" / "r.json").write_bytes(b"{}")
    copy.mkdir()
    order = []
    target = backup_copy.DirectoryTarget(copy)
    put = target.put
    target.put = lambda source, key, digest: (order.append(key), put(source, key, digest))

    first = backup_copy.copy_backup(NAME, root, target)
    assert order == [
        "files/media/objects/a.bin",
        "files/receipts/r.json",
        f"{NAME}.dump",
        f"{NAME}.json",
    ]
    assert (first["dump_copied"], first["files_copied"], first["files_copied_bytes"]) == (
        True,
        2,
        8,
    )
    assert (copy / "files" / "media" / "objects" / "a.bin").read_bytes() == b"object"
    assert (copy / f"{NAME}.dump").read_bytes() == b"PGDMP-fake"
    assert not list(copy.rglob("*.partial"))

    order.clear()
    second = backup_copy.copy_backup(NAME, root, target)
    assert (second["dump_copied"], second["files_copied"]) == (False, 0)
    assert order == [f"{NAME}.json"]
    assert backup_copy.copied_backups(target)[0][1] == NAME


def test_no_target_means_no_copy(tmp_path, monkeypatch):
    monkeypatch.delenv("BACKUP_COPY_TARGET", raising=False)
    make_backup(tmp_path)
    assert backup_copy.copy_backup(NAME, tmp_path) == {"target": "none"}


def test_a_copy_that_fails_its_checksum_is_refused_and_leaves_nothing(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"bytes")
    target = backup_copy.DirectoryTarget(tmp_path / "copy")
    with pytest.raises(backup_copy.CopyError):
        target.put(source, "dir/source.bin", "0" * 64)
    assert not [p for p in (tmp_path / "copy").rglob("*") if p.is_file()]
    with pytest.raises(backup_copy.CopyError):
        target.put(source, "../outside.bin", sha256(b"bytes").hexdigest())


def test_copy_retention_matches_the_local_folder_and_keeps_files(tmp_path):
    copy = tmp_path / "copy"
    start = datetime(2026, 11, 3, 21, 30, tzinfo=UTC)
    names = [f"{backups.PREFIX}{start - timedelta(days=day):%Y%m%dT%H%M%SZ}" for day in range(20)]
    for name in names:
        make_backup(copy, name)
    (copy / "files").mkdir()
    (copy / "files" / "kept.bin").write_bytes(b"x")
    # A dump without its manifest is an interrupted copy, not a backup to rotate.
    (copy / f"{backups.PREFIX}20250101T000000Z.dump").write_bytes(b"partial copy")
    target = backup_copy.DirectoryTarget(copy)
    removed = backup_copy.prune_copy(target)
    kept = backups.retained(backups.parse_names(names))
    assert set(removed) == set(names) - kept
    assert {name for _, name in backup_copy.copied_backups(target)} == kept
    assert (copy / "files" / "kept.bin").exists()
    assert (copy / f"{backups.PREFIX}20250101T000000Z.dump").exists()


def test_target_settings_fail_loudly(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_COPY_TARGET", "")
    assert backup_copy.copy_target() is None
    monkeypatch.setenv("BACKUP_COPY_TARGET", "directory")
    monkeypatch.setenv("BACKUP_COPY_DIR", str(tmp_path / "not-mounted"))
    with pytest.raises(backup_copy.CopyError, match="not mounted"):
        backup_copy.copy_target()
    monkeypatch.setenv("BACKUP_COPY_DIR", str(tmp_path))
    assert backup_copy.copy_target().root == tmp_path
    monkeypatch.setenv("BACKUP_COPY_TARGET", "ftp")
    with pytest.raises(backup_copy.CopyError, match="Unknown"):
        backup_copy.copy_target()
    monkeypatch.setenv("BACKUP_COPY_TARGET", "s3")
    monkeypatch.setenv("BACKUP_COPY_S3_ACCESS_KEY_ID", "configuration-test-only")
    for name in ("ENDPOINT_URL", "BUCKET", "SECRET_ACCESS_KEY"):
        monkeypatch.delenv(f"BACKUP_COPY_S3_{name}", raising=False)
    with pytest.raises(backup_copy.CopyError) as error:
        backup_copy.copy_target()
    assert "BACKUP_COPY_S3_ENDPOINT_URL" in str(error.value)
    assert "configuration-test-only" not in str(error.value)


def test_restore_from_a_folder_copy_reads_that_folder(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        backups, "restore_check", lambda url=None, **kwargs: calls.append(kwargs) or {"ok": True}
    )
    result = backup_copy.restore_check_from_copy(
        "postgresql://db/x", backup_copy.DirectoryTarget(tmp_path)
    )
    assert result == {"source": "directory", "ok": True}
    assert calls == [{"root": tmp_path}]


def s3_target():
    client = boto3.client(
        "s3",
        endpoint_url="https://ci-account.r2.cloudflarestorage.com",
        region_name="auto",
        aws_access_key_id="configuration-test-only",
        aws_secret_access_key="configuration-test-only",
    )
    return client, backup_copy.S3Target(client, "ci-backups", "/property-platform/")


def test_s3_copy_sends_its_checksum_and_verifies_what_the_provider_kept(tmp_path):
    source = tmp_path / "dump"
    source.write_bytes(b"PGDMP-fake")
    digest = sha256(b"PGDMP-fake").hexdigest()
    client, target = s3_target()
    key = {"Bucket": "ci-backups", "Key": f"property-platform/{NAME}.dump"}
    with Stubber(client) as stub:
        stub.add_response(
            "put_object",
            {},
            {
                **key,
                "Body": ANY,
                "ContentLength": 10,
                "ChecksumSHA256": ANY,
                "Metadata": {"sha256": digest},
            },
        )
        stub.add_response("head_object", {"ContentLength": 10, "Metadata": {"sha256": digest}}, key)
        target.put(source, f"{NAME}.dump", digest)
        stub.add_response("put_object", {})
        stub.add_response("head_object", {"ContentLength": 9, "Metadata": {"sha256": digest}}, key)
        with pytest.raises(backup_copy.CopyError):
            target.put(source, f"{NAME}.dump", digest)
        stub.add_client_error("head_object", "404", expected_params=key)
        assert target.describe(f"{NAME}.dump") is None
        stub.add_response(
            "list_objects_v2",
            {
                "Contents": [{"Key": f"property-platform/{NAME}.json", "Size": 3}],
                "IsTruncated": False,
            },
            {"Bucket": "ci-backups", "Prefix": "property-platform/"},
        )
        assert target.inventory("") == {f"{NAME}.json": 3}


class MemoryTarget:
    """A remote target as the restore sees it: listing, metadata and downloads only."""

    kind = "s3"

    def __init__(self, objects):
        self.objects = objects

    def inventory(self, prefix):
        return {key: len(body) for key, body in self.objects.items() if key.startswith(prefix)}

    def describe(self, key):
        body = self.objects.get(key)
        return None if body is None else (len(body), sha256(body).hexdigest())

    def fetch(self, key, destination):
        destination.write_bytes(self.objects[key])

    def local_root(self):
        return None


def test_restore_from_a_remote_copy_downloads_the_newest_backup_and_checks_objects_there(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    old = "property_platform-20261102T213000Z"
    target = MemoryTarget(
        {
            f"{old}.json": b"{}",
            f"{old}.dump": b"old",
            f"{NAME}.json": b'{"dump": "x"}',
            f"{NAME}.dump": b"new",
            f"{backups.PREFIX}20261104T213000Z.dump": b"copy interrupted before its manifest",
            "files/media/objects/a.bin": b"object",
        }
    )
    seen = {}

    def restore_check(url=None, name=None, root=None, describe=None):
        seen.update(
            name=name,
            dump=(root / f"{name}.dump").read_bytes(),
            object=describe("objects/a.bin"),
            missing=describe("objects/b.bin"),
        )
        return {"name": name, "ok": True}

    monkeypatch.setattr(backups, "restore_check", restore_check)
    result = backup_copy.restore_check_from_copy("postgresql://db/x", target)
    assert result == {"source": "s3", "name": NAME, "ok": True}
    assert seen == {
        "name": NAME,
        "dump": b"new",
        "object": (6, sha256(b"object").hexdigest()),
        "missing": None,
    }
    assert not list((tmp_path / ".copy-restore").iterdir())


class ObjectCursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, query, params=None):
        assert "evidence.stored_object" in query

    def fetchall(self):
        return self.rows


def test_objects_can_be_checked_against_a_remote_copy():
    good = b"capture body"
    copied = {
        "objects/good.bin": (len(good), sha256(good).hexdigest()),
        "objects/short.bin": (1, "0" * 64),
        "objects/changed.bin": (3, "f" * 64),
    }
    rows = [
        ("local", "objects/changed.bin", 3, "0" * 64),
        ("local", "objects/good.bin", len(good), sha256(good).hexdigest()),
        ("local", "objects/missing.bin", 4, "0" * 64),
        ("local", "objects/short.bin", 3, "0" * 64),
    ]
    summary, mismatches = backups.object_mismatches(
        ObjectCursor(rows), Path("unused"), describe=copied.get
    )
    assert summary["local"] == 4
    assert mismatches == [
        "object objects/changed.bin: copy differs from its SHA-256",
        "object objects/missing.bin: missing from the copy",
        "object objects/short.bin: copied with 1 bytes, expected 3",
    ]
