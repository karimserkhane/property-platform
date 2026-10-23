"""Operator safety net: database dumps, private file mirrors and a tested restore.

Business data stays rebuildable from migrations and Prefect pipelines; backups also
keep what pipelines cannot recreate (operator decisions, private media, archived
receipts) and make recovery fast. Files live under BACKUP_DIR, never in Git or an
image. Credentials go to PostgreSQL tools through the environment, never argv.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
from psycopg import sql

PREFIX = "property_platform-"
STAMP = "%Y%m%dT%H%M%SZ"
DAILY_KEEP = 7
WEEKLY_KEEP = 4
SCHEMAS = ("real_estate", "evidence")
# Mounted private trees mirrored next to the dumps (see compose.ingestion.yaml).
MIRRORED = {"media": Path("/media"), "receipts": Path("/data")}
DUMP_TIMEOUT = 3600


def backup_root() -> Path:
    return Path(os.environ.get("BACKUP_DIR", "/backups"))


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise ValueError("DATABASE_URL is required for backups")
    return url


def pg_environment(url: str, database: str | None = None) -> dict:
    """libpq variables for pg_dump/pg_restore, so no secret appears in a process list."""
    parts = urlsplit(url)
    if parts.scheme not in {"postgres", "postgresql"} or not parts.hostname:
        raise ValueError("Unsupported database URL")
    return {
        **os.environ,
        "PGHOST": parts.hostname,
        "PGPORT": str(parts.port or 5432),
        "PGUSER": unquote(parts.username or ""),
        "PGPASSWORD": unquote(parts.password or ""),
        "PGDATABASE": database or parts.path.lstrip("/"),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table_counts(cursor) -> dict[str, int]:
    cursor.execute(
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE table_type = 'BASE TABLE' AND table_schema = ANY(%s) ORDER BY 1, 2",
        [list(SCHEMAS)],
    )
    counts = {}
    for schema, table in cursor.fetchall():
        cursor.execute(
            sql.SQL("SELECT count(*) FROM {}.{}").format(
                sql.Identifier(schema), sql.Identifier(table)
            )
        )
        counts[f"{schema}.{table}"] = cursor.fetchone()[0]
    return counts


def create_backup(now: datetime | None = None, url: str | None = None) -> dict:
    """Dump the database from one exported snapshot and record its row counts.

    The counts and pg_dump read the same snapshot, so a later restore check compares
    like with like even while collections keep writing.
    """
    now = now or datetime.now(UTC)
    url = url or database_url()
    root = backup_root()
    root.mkdir(parents=True, exist_ok=True)
    name = f"{PREFIX}{now.strftime(STAMP)}"
    partial = root / f".{name}.dump.partial"
    with psycopg.connect(url, autocommit=False) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            cursor.execute("SELECT pg_export_snapshot(), current_setting('server_version')")
            snapshot, server_version = cursor.fetchone()
            counts = table_counts(cursor)
            subprocess.run(
                [
                    "pg_dump",
                    "--format=custom",
                    "--compress=6",
                    f"--snapshot={snapshot}",
                    f"--file={partial}",
                ],
                env=pg_environment(url),
                check=True,
                timeout=DUMP_TIMEOUT,
            )
        connection.rollback()
    dump = root / f"{name}.dump"
    partial.replace(dump)
    manifest = {
        "name": name,
        "created_at": now.isoformat(),
        "server_version": server_version,
        "dump": dump.name,
        "bytes": dump.stat().st_size,
        "sha256": _sha256(dump),
        "tables": counts,
        "files": mirror_private_files(root),
    }
    (root / f"{name}.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {key: manifest[key] for key in ("name", "bytes", "sha256", "files")} | {
        "tables": len(counts),
        "rows": sum(counts.values()),
    }


def mirror_private_files(root: Path, sources: dict[str, Path] | None = None) -> dict:
    """Copy new or changed private files; mirrored files are never deleted here."""
    summary = {}
    for label, source in (sources or MIRRORED).items():
        copied = total = size = 0
        if source.is_dir():
            target = root / "files" / label
            for path in source.rglob("*"):
                if not path.is_file() or path.is_symlink():
                    continue
                total += 1
                size += path.stat().st_size
                destination = target / path.relative_to(source)
                stat = path.stat()
                if destination.exists():
                    current = destination.stat()
                    if (current.st_size, int(current.st_mtime)) == (
                        stat.st_size,
                        int(stat.st_mtime),
                    ):
                        continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
                copied += 1
        summary[label] = {"files": total, "bytes": size, "copied": copied}
    return summary


def backups(root: Path | None = None) -> list[tuple[datetime, str]]:
    found = []
    for manifest in (root or backup_root()).glob(f"{PREFIX}*.json"):
        match = re.fullmatch(rf"{re.escape(PREFIX)}(\d{{8}}T\d{{6}}Z)", manifest.stem)
        if match and (manifest.with_suffix(".dump")).exists():
            found.append((datetime.strptime(match[1], STAMP).replace(tzinfo=UTC), manifest.stem))
    return sorted(found, reverse=True)


def retained(found: list[tuple[datetime, str]]) -> set[str]:
    """Newest DAILY_KEEP backups plus the newest backup of each of WEEKLY_KEEP ISO weeks."""
    keep = {name for _, name in found[:DAILY_KEEP]}
    weeks = []
    for moment, name in found:
        week = moment.isocalendar()[:2]
        if week not in weeks:
            weeks.append(week)
            if len(weeks) <= WEEKLY_KEEP:
                keep.add(name)
    return keep


def prune(root: Path | None = None) -> list[str]:
    root = root or backup_root()
    found = backups(root)
    keep = retained(found)
    removed = []
    for _, name in found:
        if name not in keep:
            for suffix in (".dump", ".json"):
                (root / f"{name}{suffix}").unlink(missing_ok=True)
            removed.append(name)
    return removed


def compare_counts(expected: dict[str, int], restored: dict[str, int]) -> list[str]:
    return [
        f"{table}: expected {count}, restored {restored.get(table)}"
        for table, count in sorted(expected.items())
        if restored.get(table) != count
    ] + [f"{table}: not in the backup manifest" for table in sorted(set(restored) - set(expected))]


def restore_check(url: str | None = None, name: str | None = None) -> dict:
    """Restore the newest (or named) dump into a throwaway database and compare counts."""
    url = url or database_url()
    root = backup_root()
    found = backups(root)
    if not found:
        raise FileNotFoundError("No backup to check")
    name = name or found[0][1]
    manifest = json.loads((root / f"{name}.json").read_text(encoding="utf-8"))
    dump = root / manifest["dump"]
    if _sha256(dump) != manifest["sha256"]:
        return {"name": name, "ok": False, "mismatches": ["dump checksum differs from manifest"]}
    scratch = f"restore_check_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(scratch)))
    try:
        subprocess.run(
            [
                "pg_restore",
                "--no-owner",
                "--no-privileges",
                "--exit-on-error",
                f"--dbname={scratch}",
                str(dump),
            ],
            env=pg_environment(url, scratch),
            check=True,
            timeout=DUMP_TIMEOUT,
        )
        parts = urlsplit(url)
        with psycopg.connect(parts._replace(path=f"/{scratch}").geturl()) as restored:
            with restored.cursor() as cursor:
                counts = table_counts(cursor)
    finally:
        with psycopg.connect(url, autocommit=True) as admin:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(scratch))
            )
    mismatches = compare_counts(manifest["tables"], counts)
    return {
        "name": name,
        "ok": not mismatches,
        "tables": len(counts),
        "rows": sum(counts.values()),
        "mismatches": mismatches,
    }
