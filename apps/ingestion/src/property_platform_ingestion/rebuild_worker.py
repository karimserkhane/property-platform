"""Synchronous Django process for the private Prefect rebuild controller."""

import hashlib
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit


def require_empty_target(database, expected_name):
    """Check the actual SQL connection too; environment parsing alone is insufficient."""
    with database.cursor() as cursor:
        cursor.execute(
            "SELECT current_database(), EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_schema IN ('public','real_estate','evidence'))"
        )
        actual_name, has_tables = cursor.fetchone()
        if actual_name != expected_name or has_tables:
            raise ValueError("Rebuild replay requires its own completely empty database")


def main():
    import django

    django.setup()
    from django.core.management import call_command
    from django.db import connections
    from property_platform.modules.evidence.rebuild_archive import export_archive, replay_archive

    from .rebuilds import SCRATCH

    root = Path(os.environ["REBUILD_ARCHIVE_DIR"])
    try:
        if sys.argv[1:] == ["export"]:
            export_archive(root)
        elif sys.argv[1:] == ["replay"]:
            name = urlsplit(os.environ["DATABASE_URL"]).path.lstrip("/")
            if not SCRATCH.fullmatch(name):
                raise ValueError("Only a generated rebuild-check database can be migrated")
            digest = hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
            if digest != os.environ["REBUILD_MANIFEST_SHA256"]:
                raise ValueError("Replay manifest changed after export")
            require_empty_target(connections["default"], name)
            # The controller created an empty template0 database. Migrate explicitly;
            # this is never a startup hook and is never run against the source.
            call_command("migrate", interactive=False, verbosity=0)
            replay_archive(root, os.environ["REBUILD_ACTOR"], os.environ["REBUILD_RUN_ID"])
        else:
            raise ValueError("Unknown rebuild worker action")
    finally:
        connections.close_all()


if __name__ == "__main__":
    main()
