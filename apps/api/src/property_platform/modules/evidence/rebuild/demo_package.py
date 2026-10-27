"""Versioned demonstration package for browser journeys in CI (A13), never a dump.

Owner decisions of 25 and 27 October 2026 (A13, A18): real captures, limited to the
journeys, are kept in the public repository with provenance, licence and capture date
per file; developer and listing pages are excluded. The package is an A04 replay
manifest restricted to reviewed acquisitions; the current typed importers rebuild its
rows in an empty, disposable database only.
"""

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

from property_platform.modules.catalog.models import Project

from ..models import Capture, IngestionRun
from .rebuild_archive import VERSION, export_archive, replay_archive, write_json

KIND = "demo"
SELECTION = "selection.json"


def read_selection(root: Path):
    """Reviewed acquisitions with the licence or terms stated by a person, never guessed."""
    selection = json.loads((root / SELECTION).read_text("utf-8"))
    runs = selection["runs"]
    for item in runs:
        UUID(item["run"])
        for field in ("source", "why", "licence"):
            if not str(item.get(field, "")).strip():
                raise ValueError(f"Selected run {item['run']} requires {field}")
    if len({item["run"] for item in runs}) != len(runs):
        raise ValueError("A run is selected twice")
    return runs


def export_package(root: Path):
    """Write manifest, blobs and provenance for the selected runs from this database.

    Reads only (A04 export transaction). Bytes no longer selected are removed so the
    package holds exactly what its manifest replays.
    """
    runs = read_selection(root)
    by_run = {item["run"]: item for item in runs}
    found = {
        str(run.pk): run
        for run in IngestionRun.objects.select_related("source").filter(pk__in=list(by_run))
    }
    missing = sorted(set(by_run) - set(found))
    if missing:
        raise ValueError(f"Selected runs absent from this database: {', '.join(missing)}")
    for key, run in found.items():
        if run.source.key != by_run[key]["source"]:
            raise ValueError(f"Selected run {key} belongs to {run.source.key}")
    with tempfile.TemporaryDirectory() as scratch:
        work = Path(scratch)
        export_archive(work, runs=list(by_run))
        full = json.loads((work / "manifest.json").read_text("utf-8"))
        exported = {step["run"] for step in full["steps"]}
        if exported != set(by_run):
            absent = ", ".join(sorted(set(by_run) - exported))
            raise ValueError(f"Selected runs without a replay step: {absent}")
        # Only replay instructions: no expected counts or published state of the
        # complete reference database, which this subset does not reproduce.
        manifest = {
            "version": VERSION,
            "kind": KIND,
            "snapshot_at": full["snapshot_at"],
            "steps": full["steps"],
            "scenes": [],
            "tiles": [],
            "omitted": full["omitted"],
        }
        blobs = root / "blobs"
        if blobs.exists():
            shutil.rmtree(blobs)
        blobs.mkdir()
        provenance = []
        for step in manifest["steps"]:
            item = by_run[step["run"]]
            for capture in step["captures"]:
                digest = capture["sha256"]
                if not (blobs / digest).exists():
                    shutil.copyfile(work / "blobs" / digest, blobs / digest)
                receipt = capture["receipt"]
                provenance.append(
                    {
                        "sha256": digest,
                        "byte_length": capture["byte_length"],
                        "source": item["source"],
                        "run": step["run"],
                        "url": receipt["url"],
                        "http_status": receipt["http_status"],
                        "fetched_at": receipt["fetched_at"],
                        "licence": item["licence"],
                    }
                )
    write_json(root / "manifest.json", manifest)
    write_json(root / "provenance.json", provenance)
    return {
        "steps": len(manifest["steps"]),
        "captures": len(provenance),
        "bytes": sum(path.stat().st_size for path in blobs.iterdir()),
    }


def verify_package(root: Path):
    """Every blob is declared with provenance, and every declared blob is intact."""
    manifest = json.loads((root / "manifest.json").read_text("utf-8"))
    if manifest.get("kind") != KIND or manifest["version"] != VERSION:
        raise ValueError("Not a demonstration replay package")
    provenance = json.loads((root / "provenance.json").read_text("utf-8"))
    declared = {row["sha256"] for row in provenance}
    replayed = {c["sha256"] for step in manifest["steps"] for c in step["captures"]}
    present = {path.name for path in (root / "blobs").iterdir()}
    if not declared == replayed == present:
        raise ValueError("Package bytes, manifest and provenance differ")
    for row in provenance:
        payload = (root / "blobs" / row["sha256"]).read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if len(payload) != row["byte_length"] or digest != row["sha256"]:
            raise ValueError("Package capture checksum or size differs")
        if not str(row.get("licence", "")).strip():
            raise ValueError("Package capture without licence statement")
    return manifest


def load_package(root: Path, actor: str):
    """Replay the package into this database, which must hold no source capture yet.

    Never a merge into a database in service: a single existing capture refuses the
    load. A failed or diverging step fails the load; table totals are not compared,
    because the package is a subset of the reference database.
    """
    manifest = verify_package(root)
    if Capture.objects.exists() or IngestionRun.objects.exists():
        raise ValueError("Demonstration package loads only into an empty database")
    with tempfile.TemporaryDirectory() as scratch:
        replay_archive(root, actor, str(uuid4()), report_root=Path(scratch))
        report = json.loads((Path(scratch) / "report.json").read_text("utf-8"))
    failed = [
        step for step in report["steps"] if step["status"] == "failed" or "diverged_from" in step
    ]
    if failed:
        raise ValueError(f"Demonstration replay failed: {json.dumps(failed)}")
    return {"steps": len(manifest["steps"]), "projects": Project.objects.count()}
