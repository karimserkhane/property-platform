"""Private, content-addressed source receipts for rebuilding the project catalogue.

These are acquisition proofs, never serialized ORM rows or a database dump.
Replays keep the source bytes and original acquisition clock. The current closed
registry and pure extractors validate every proof again before a database write.
"""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from property_platform.modules.evidence.project_protocol import (
    extract_project_source,
    project_registry,
    project_urls,
    validate_project_receipts,
)

from .storage import MAX_RECEIPT, _read_receipt

MAX_VERSIONS = 10000


def project_source_scope(project, source):
    return (
        f"{project['territory_id']}:{project['slug']}:"
        + hashlib.sha256(source["url"].encode()).hexdigest()
    )


def _folder(root, scope):
    if len(scope.split(":")) != 3:
        raise ValueError("Archive requires one reviewed project source")
    definitions = project_registry(scope)
    root = Path(root).resolve()
    archive = root / "project-source-archive"
    folder = archive / hashlib.sha256(scope.encode()).hexdigest()
    if archive.is_symlink() or folder.is_symlink() or folder.resolve().parent != archive:
        raise ValueError("Project source archive escapes its configured root")
    return folder, definitions


def _validate(rows, definitions):
    receipts = validate_project_receipts(rows, definitions)
    for project in definitions:
        for source in project["sources"]:
            extract_project_source(project, source, receipts[source["url"]])
    return receipts


def archive_project_batch(root, scope, rows):
    folder, definitions = _folder(root, scope)
    _validate(rows, definitions)
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    if len(encoded) > MAX_RECEIPT:
        raise ValueError("Project source archive exceeds its receipt budget")
    key = hashlib.sha256(encoded).hexdigest()
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{key}.json"
    if destination.exists():
        read_project_batch(root, scope, key)
        return key
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=folder, prefix="pending-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            pass
        read_project_batch(root, scope, key)
        return key
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_project_batch(root, scope, key):
    if not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{64}", key):
        raise ValueError("Invalid project source archive identity")
    folder, definitions = _folder(root, scope)
    path = folder / f"{key}.json"
    rows = _read_receipt(path)
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(encoded).hexdigest() != key:
        raise ValueError("Project source archive integrity check failed")
    _validate(rows, definitions)
    return rows


def project_batches(root, scope):
    """Oldest to newest, so rebuilding preserves source history as well as facts."""
    folder, definitions = _folder(root, scope)
    if not folder.exists():
        return ()
    versions = []
    for path in folder.glob("*.json"):
        if len(versions) >= MAX_VERSIONS:
            raise ValueError("Project source history exceeds its explicit version budget")
        rows = read_project_batch(root, scope, path.stem)
        receipts = validate_project_receipts(rows, definitions)
        observed_at = max(row["fetched_at"] for row in receipts.values())
        versions.append((observed_at, path.stem))
    return tuple(key for _, key in sorted(versions))


def index_project_checkpoints(root):
    """Adopt existing validated collector checkpoints without needing the old DB."""
    root = Path(root).resolve()
    from property_platform.modules.evidence.project_discovery import catalogue_registry

    catalogues = {}
    for definition in catalogue_registry():
        scope = f"{definition['territory_scope']}:{definition['key']}"
        catalogues.setdefault(definition["url"], []).append(scope)
    scopes = {}
    for project in project_registry():
        for source in project["sources"]:
            if source["role"] != "terms":
                scope = project_source_scope(project, source)
                scopes.setdefault(source["url"], []).append(scope)
    summary = {"checkpoints": 0, "indexed": 0, "rejected": 0}
    folder = root / "receipts"
    if folder.is_symlink():
        raise ValueError("Checkpoint folder cannot be a symbolic link")
    for path in folder.glob("*.json"):
        rows = _read_receipt(path)
        summary["checkpoints"] += 1
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            continue
        by_url = {row.get("url"): row for row in rows}
        for url in by_url.keys() & catalogues.keys():
            for scope in catalogues[url]:
                try:
                    archive_catalogue_batch(root, scope, [by_url[url]])
                    summary["indexed"] += 1
                except ValueError:
                    summary["rejected"] += 1
        for url in by_url.keys() & scopes.keys():
            for scope in scopes[url]:
                required = project_urls(project_registry(scope))
                if not set(required) <= by_url.keys():
                    continue
                try:
                    archive_project_batch(root, scope, [by_url[url] for url in required])
                    summary["indexed"] += 1
                except ValueError:
                    summary["rejected"] += 1
    return summary


def _catalogue_folder(root, scope):
    from property_platform.modules.evidence.project_discovery import catalogue_for

    definition = catalogue_for(scope)
    archive = Path(root).resolve() / "project-catalogue-archive"
    folder = archive / hashlib.sha256(scope.encode()).hexdigest()
    if archive.is_symlink() or folder.is_symlink() or folder.resolve().parent != archive:
        raise ValueError("Project catalogue archive escapes its configured root")
    return folder, definition


def _validate_catalogue(rows, definition):
    from property_platform.modules.evidence.project_discovery import (
        candidates_for,
        catalogue_byte_limit,
    )
    from property_platform.modules.evidence.property_protocol import validate_receipts

    receipts = validate_receipts(
        rows, {definition["url"]}, max_bytes=catalogue_byte_limit(definition)
    )
    candidates_for(definition, receipts[definition["url"]]["payload"])
    return receipts


def archive_catalogue_batch(root, scope, rows):
    folder, definition = _catalogue_folder(root, scope)
    _validate_catalogue(rows, definition)
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    if len(encoded) > MAX_RECEIPT:
        raise ValueError("Project catalogue archive exceeds its receipt budget")
    key = hashlib.sha256(encoded).hexdigest()
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{key}.json"
    temporary = None
    try:
        if not destination.exists():
            with tempfile.NamedTemporaryFile(dir=folder, prefix="pending-", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, destination)
            except FileExistsError:
                pass
        read_catalogue_batch(root, scope, key)
        return key
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_catalogue_batch(root, scope, key):
    if not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{64}", key):
        raise ValueError("Invalid project catalogue archive identity")
    folder, definition = _catalogue_folder(root, scope)
    rows = _read_receipt(folder / f"{key}.json")
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(encoded).hexdigest() != key:
        raise ValueError("Project catalogue archive integrity check failed")
    _validate_catalogue(rows, definition)
    return rows


def catalogue_batches(root, scope):
    folder, definition = _catalogue_folder(root, scope)
    if not folder.exists():
        return ()
    versions = []
    for path in folder.glob("*.json"):
        if len(versions) >= MAX_VERSIONS:
            raise ValueError("Project catalogue history exceeds its explicit version budget")
        rows = read_catalogue_batch(root, scope, path.stem)
        receipts = _validate_catalogue(rows, definition)
        versions.append((receipts[definition["url"]]["fetched_at"], path.stem))
    return tuple(key for _, key in sorted(versions))
