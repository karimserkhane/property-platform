"""Check source reconstruction in an isolated database, never restore over the source.

Only a fresh, internally generated name can be migrated, replayed and dropped.
The source is opened read-only by the export worker. No source URL or target name
is accepted as a Prefect parameter, and no password reaches argv or a flow result.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import uuid4

import psycopg
from psycopg import sql

from .backups import backup_root, database_url

TIMEOUT = 7200
SCRATCH = re.compile(r"rebuild_check_[0-9a-f]{32}")


def scratch_url(source: str, name: str) -> str:
    parts = urlsplit(source)
    if (
        not SCRATCH.fullmatch(name)
        or parts.scheme not in {"postgres", "postgresql"}
        or not parts.hostname
        or unquote(parts.path.lstrip("/")) == name
    ):
        raise ValueError("Rebuild target must be an internally generated scratch database")
    # A source query may contain libpq service/dbname options. Do not forward them
    # to the target; explicit host/credentials are retained, never a database alias.
    if parts.query or parts.fragment:
        raise ValueError("Rebuild source requires a plain PostgreSQL URL without options")
    return parts._replace(path=f"/{name}").geturl()


def worker(action: str, root: Path, url: str, *, actor: str, run_id: str, manifest_hash=""):
    environment = {
        **os.environ,
        "DATABASE_URL": url,
        "REBUILD_ARCHIVE_DIR": str(root),
        "REBUILD_ACTOR": actor,
        "REBUILD_RUN_ID": run_id,
        "REBUILD_MANIFEST_SHA256": manifest_hash,
    }
    # The source export doesn't receive the PostgreSQL admin connection separately.
    subprocess.run(
        [sys.executable, "-m", "property_platform_ingestion.rebuild_worker", action],
        env=environment,
        check=True,
        timeout=TIMEOUT,
    )


def rebuild_check(*, actor: str, run_id: str, url: str | None = None) -> dict:
    from uuid import UUID

    UUID(str(run_id))
    if not isinstance(actor, str) or not 1 <= len(actor.strip()) <= 80:
        raise ValueError("An audited operator is required")
    source = url or database_url()
    name = f"rebuild_check_{uuid4().hex}"
    target = scratch_url(source, name)
    root = backup_root() / "rebuild-checks" / str(run_id)
    # No overwrite of a previous report/bundle; retries are explicit new runs.
    root.mkdir(parents=True, exist_ok=False)
    actor = f"Prefect/{run_id}/{actor.strip()}"
    try:
        worker("export", root, source, actor=actor, run_id=run_id)
    except BaseException:
        # An interrupted export is not an operator bundle; remove only this new directory.
        shutil.rmtree(root)
        raise
    manifest_hash = hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
    created = False
    try:
        with psycopg.connect(source, autocommit=True) as admin:
            admin.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name))
            )
        created = True
        worker("replay", root, target, actor=actor, run_id=run_id, manifest_hash=manifest_hash)
        report = json.loads((root / "report.json").read_text("utf-8"))
    finally:
        try:
            if created:
                # No FORCE: an unexpected remaining session makes cleanup fail visibly.
                # This exact name was created successfully in this invocation only.
                with psycopg.connect(source, autocommit=True) as admin:
                    admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
        finally:
            # The bytes remain in the source database and A03 backups. Keep the manifest
            # and report for the operator, not a growing private copy of every capture.
            if (root / "blobs").exists():
                shutil.rmtree(root / "blobs")
    return {
        "ok": report["ok"],
        "tables": len(report["tables"]),
        "failed_steps": report["failed_steps"],
        "diverged_steps": report["diverged_steps"],
        "mismatches": report["mismatches"],
        "source_snapshot_at": report["source_snapshot_at"],
        "archive": str(root),
        "report": str(root / "report.json"),
        "manifest_sha256": manifest_hash,
    }
