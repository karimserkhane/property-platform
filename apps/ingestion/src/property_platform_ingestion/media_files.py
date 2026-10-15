"""Explicit operator manifest intake. No downloads, approval or publication here."""

import json
import re
from pathlib import Path
from uuid import UUID

from .runtime import checked_receipt_path


def manifest_files(root, name):
    root = Path(root)
    path = checked_receipt_path(root, name)
    if path.stat().st_size > 64 * 1024:
        raise ValueError("Media manifest exceeds its budget")
    raw = path.read_bytes()
    if len(raw) > 64 * 1024:
        raise ValueError("Media manifest exceeds its budget")
    entries = json.loads(raw)
    if not isinstance(entries, list) or not 1 <= len(entries) <= 20:
        raise ValueError("Manifest must contain 1–20 files")
    result, seen = [], set()
    directory = (root / "media").resolve()
    if (root / "media").is_symlink() or directory.parent != root.resolve():
        raise ValueError("Media intake directory escapes private storage")
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"media_id", "filename"}:
            raise ValueError("Invalid media manifest entry")
        identity = str(UUID(entry["media_id"]))
        filename = entry["filename"]
        if not isinstance(filename, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}", filename
        ):
            raise ValueError("Media filename must be a plain filename")
        path = directory / filename
        if (
            path.is_symlink()
            or path.resolve().parent != directory
            or not path.is_file()
            or identity in seen
        ):
            raise ValueError("Media file missing, duplicated or outside intake directory")
        seen.add(identity)
        result.append((identity, path))
    return result


def ingest_files(root, name, *, actor):
    from property_platform.modules.evidence.project_media_storage import attach_project_media_file

    entries = manifest_files(root, name)  # Validate the entire manifest before mutating data.
    captures = [
        str(attach_project_media_file(identity, path, actor=actor).id) for identity, path in entries
    ]
    return {"files": len(captures), "capture_ids": captures}
