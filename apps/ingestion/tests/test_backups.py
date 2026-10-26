"""Backup bookkeeping without a database server: snapshots, retention, mirrors, checks."""

import json
import os
from datetime import UTC, datetime, timedelta

import pytest

from property_platform_ingestion import backups

URL = "postgresql://platform:p%40ss%3Aword@db:5432/property_platform"


def test_credentials_reach_tools_through_the_environment_only():
    env = backups.pg_environment(URL)
    assert (env["PGHOST"], env["PGPORT"], env["PGUSER"]) == ("db", "5432", "platform")
    assert env["PGPASSWORD"] == "p@ss:word"
    assert env["PGDATABASE"] == "property_platform"
    assert backups.pg_environment(URL, "scratch")["PGDATABASE"] == "scratch"
    with pytest.raises(ValueError):
        backups.pg_environment("mysql://db/property_platform")


def stamps(days):
    start = datetime(2026, 10, 23, 1, 30, tzinfo=UTC)
    return [
        (
            start - timedelta(days=day),
            f"{backups.PREFIX}{(start - timedelta(days=day)):%Y%m%dT%H%M%SZ}",
        )
        for day in range(days)
    ]


def test_retention_keeps_seven_days_and_one_backup_for_each_of_four_weeks():
    found = stamps(40)
    keep = backups.retained(found)
    daily = {name for _, name in found[:7]}
    assert daily <= keep
    weeks = {moment.isocalendar()[:2] for moment, name in found if name in keep}
    assert len(weeks) == 4
    assert len(keep) <= 7 + 4
    assert found[-1][1] not in keep


def test_prune_removes_only_dumps_outside_retention(tmp_path):
    found = stamps(20)
    for _, name in found:
        (tmp_path / f"{name}.dump").write_bytes(b"dump")
        (tmp_path / f"{name}.json").write_text("{}")
    (tmp_path / "files").mkdir()
    (tmp_path / "files" / "kept.bin").write_bytes(b"x")
    removed = backups.prune(tmp_path)
    kept = backups.retained(found)
    assert set(removed) == {name for _, name in found} - kept
    assert {name for _, name in backups.backups(tmp_path)} == kept
    assert (tmp_path / "files" / "kept.bin").exists()


def test_mirror_copies_new_and_changed_files_and_never_deletes(tmp_path):
    source, root = tmp_path / "media", tmp_path / "backups"
    (source / "a").mkdir(parents=True)
    (source / "a" / "one.bin").write_bytes(b"1")
    (source / "two.bin").write_bytes(b"22")
    first = backups.mirror_private_files(root, {"media": source})
    assert first["media"] == {"files": 2, "bytes": 3, "copied": 2}
    assert backups.mirror_private_files(root, {"media": source})["media"]["copied"] == 0
    (source / "two.bin").write_bytes(b"333")
    (source / "a" / "one.bin").unlink()
    third = backups.mirror_private_files(root, {"media": source})["media"]
    assert (third["files"], third["copied"]) == (1, 1)
    assert (root / "files" / "media" / "a" / "one.bin").read_bytes() == b"1"
    assert (
        backups.mirror_private_files(root, {"missing": tmp_path / "none"})["missing"]["files"] == 0
    )


def test_count_comparison_reports_differences_and_unknown_tables():
    assert backups.compare_counts({"evidence.capture": 2}, {"evidence.capture": 2}) == []
    assert backups.compare_counts(
        {"evidence.capture": 2, "real_estate.parcel": 5},
        {"evidence.capture": 1, "evidence.extra": 0},
    ) == [
        "evidence.capture: expected 2, restored 1",
        "real_estate.parcel: expected 5, restored None",
        "evidence.extra: not in the backup manifest",
    ]


class Cursor:
    def __init__(self, log):
        self.log, self.result = log, None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, query, params=None):
        text = query if isinstance(query, str) else repr(query)
        self.log.append(text)
        if "pg_export_snapshot" in text:
            self.result = [("00000003-0000001B-1", "18.6")]
        elif "information_schema.tables" in text:
            self.result = [("evidence", "capture"), ("real_estate", "parcel")]
        else:
            self.result = [(7,)]

    def fetchone(self):
        return self.result[0]

    def fetchall(self):
        return self.result


class Connection:
    def __init__(self, log):
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return Cursor(self.log)

    def rollback(self):
        self.log.append("ROLLBACK")


def test_backup_dumps_the_counted_snapshot_and_writes_its_manifest(tmp_path, monkeypatch):
    log, commands = [], []
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backups, "MIRRORED", {})
    monkeypatch.setattr(backups.psycopg, "connect", lambda *a, **k: Connection(log))

    def run(command, env, check, timeout):
        commands.append((command, env))
        target = next(part.split("=", 1)[1] for part in command if part.startswith("--file="))
        with open(target, "wb") as handle:
            handle.write(b"PGDMP-fake")

    monkeypatch.setattr(backups.subprocess, "run", run)
    summary = backups.create_backup(datetime(2026, 10, 23, 1, 30, tzinfo=UTC), URL)
    assert summary["name"] == "property_platform-20261023T013000Z"
    assert (summary["tables"], summary["rows"]) == (2, 14)
    [(command, env)] = commands
    assert "--snapshot=00000003-0000001B-1" in command
    assert not any("p@ss" in part or "p%40ss" in part for part in command)
    assert env["PGPASSWORD"] == "p@ss:word"
    assert log[0].startswith("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    manifest = json.loads((tmp_path / f"{summary['name']}.json").read_text())
    assert manifest["tables"] == {"evidence.capture": 7, "real_estate.parcel": 7}
    assert manifest["sha256"] == summary["sha256"]
    assert manifest["bytes"] == len(b"PGDMP-fake")
    assert not [p for p in os.listdir(tmp_path) if p.endswith(".partial")]


def test_restore_check_refuses_a_dump_whose_checksum_changed(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    name = "property_platform-20261023T013000Z"
    (tmp_path / f"{name}.dump").write_bytes(b"tampered")
    (tmp_path / f"{name}.json").write_text(
        json.dumps({"dump": f"{name}.dump", "sha256": "0" * 64, "tables": {}})
    )
    monkeypatch.setattr(
        backups.psycopg, "connect", lambda *a, **k: pytest.fail("no database expected")
    )
    result = backups.restore_check(URL)
    assert result == {
        "name": name,
        "ok": False,
        "mismatches": ["dump checksum differs from manifest"],
    }


class ObjectCursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, query, params=None):
        assert "evidence.stored_object" in query

    def fetchall(self):
        return self.rows


def test_objects_referenced_by_the_dump_must_be_mirrored_with_size_and_checksum(tmp_path):
    from hashlib import sha256

    mirror = tmp_path / "files" / "media"
    good, changed = b"capture body", b"other body"
    (mirror / "objects" / "sha256" / "ab").mkdir(parents=True)
    (mirror / "objects" / "sha256" / "ab" / "good.bin").write_bytes(good)
    (mirror / "objects" / "sha256" / "ab" / "changed.bin").write_bytes(b"XXXXX body")
    (mirror / "objects" / "sha256" / "ab" / "short.bin").write_bytes(b"x")
    rows = [
        ("local", "objects/sha256/ab/changed.bin", len(changed), sha256(changed).hexdigest()),
        ("local", "objects/sha256/ab/good.bin", len(good), sha256(good).hexdigest()),
        ("local", "objects/sha256/ab/missing.bin", 4, "0" * 64),
        ("local", "objects/sha256/ab/short.bin", 3, "0" * 64),
        ("local", "../outside.bin", 3, "0" * 64),
        ("s3", "objects/sha256/cd/remote.bin", 9, "1" * 64),
    ]
    summary, mismatches = backups.object_mismatches(ObjectCursor(rows), mirror)
    assert summary == {
        "local": 5,
        "local_bytes": len(changed) + len(good) + 4 + 3 + 3,
        "remote": 1,
    }
    assert mismatches == [
        "object objects/sha256/ab/changed.bin: mirrored copy differs from its SHA-256",
        "object objects/sha256/ab/missing.bin: missing from the mirror",
        "object objects/sha256/ab/short.bin: mirrored with 1 bytes, expected 3",
        "object ../outside.bin: escapes the mirror",
    ]


def test_object_mismatch_lines_are_capped_but_counted(tmp_path, monkeypatch):
    monkeypatch.setattr(backups, "MISMATCH_LINES", 2)
    rows = [("local", f"objects/{index}.bin", 1, "0" * 64) for index in range(5)]
    summary, mismatches = backups.object_mismatches(ObjectCursor(rows), tmp_path)
    assert summary["local"] == 5
    assert mismatches[-1] == "3 more object mismatches"
    assert len(mismatches) == 3
