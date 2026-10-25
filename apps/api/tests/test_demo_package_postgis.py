"""Demonstration package (A13): reviewed subset, provenance per byte, empty target only."""

import hashlib
import json
import os
from datetime import UTC, datetime
from urllib.parse import urlencode

import pytest

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Demonstration replay requires real PostGIS", allow_module_level=True)

from property_platform.modules.catalog.models import Parcel  # noqa: E402
from property_platform.modules.evidence import demo_package, onwani  # noqa: E402
from property_platform.modules.evidence import rebuild_archive as archive  # noqa: E402
from property_platform.modules.evidence.models import Capture, IngestionRun, Source  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

LICENCE = "Test fixture licence statement"


def onwani_run(payload=b"{}"):
    source = Source.objects.get_or_create(
        key="dmt:onwani:smarthub:plot:adm:reem", defaults={"name": "Test", "url": onwani.BASE_URL}
    )[0]
    run = IngestionRun.objects.create(source=source, actor="test", connector_version="test")
    run.status, run.finished_at = "succeeded", datetime.now(UTC)
    run.save(update_fields=["status", "finished_at"])
    stamp = datetime(2026, 10, 1, tzinfo=UTC)
    Capture.objects.create(
        run=run,
        payload=payload,
        url=onwani.BASE_URL,
        http_status=200,
        fetched_at=stamp,
        fetched_started_at=stamp,
        byte_length=len(payload),
        content_sha256=hashlib.sha256(payload).hexdigest(),
    )
    return run


def select(root, *items):
    root.mkdir(exist_ok=True)
    (root / "selection.json").write_text(json.dumps({"runs": list(items)}), "utf-8")


def test_export_keeps_only_the_selected_runs_with_provenance(tmp_path):
    kept, other = onwani_run(b'{"kept": true}'), onwani_run(b'{"other": true}')
    package = tmp_path / "package"
    select(
        package,
        {"run": str(kept.pk), "source": kept.source.key, "why": "parcels", "licence": LICENCE},
    )
    (package / "blobs").mkdir()
    (package / "blobs" / "stale").write_bytes(b"no longer selected")
    summary = demo_package.export_package(package)
    manifest = json.loads((package / "manifest.json").read_text())
    assert summary == {"steps": 1, "captures": 1, "bytes": len(b'{"kept": true}')}
    assert manifest["kind"] == "demo"
    assert [step["run"] for step in manifest["steps"]] == [str(kept.pk)]
    # No expected totals or published state of the complete reference database.
    assert not {"expected", "published", "identities"} & set(manifest)
    provenance = json.loads((package / "provenance.json").read_text())
    assert provenance == [
        {
            "sha256": hashlib.sha256(b'{"kept": true}').hexdigest(),
            "byte_length": 14,
            "source": kept.source.key,
            "run": str(kept.pk),
            "url": onwani.BASE_URL,
            "http_status": 200,
            "fetched_at": "2026-10-01T00:00:00+00:00",
            "licence": LICENCE,
        }
    ]
    assert [path.name for path in (package / "blobs").iterdir()] == [provenance[0]["sha256"]]
    assert str(other.pk) not in (package / "manifest.json").read_text()


def test_export_refuses_an_unreviewed_or_mismatched_selection(tmp_path):
    run = onwani_run()
    package = tmp_path / "package"
    select(package, {"run": str(run.pk), "source": run.source.key, "why": "parcels"})
    with pytest.raises(ValueError, match="licence"):
        demo_package.export_package(package)
    select(package, {"run": str(run.pk), "source": "osm:reem:osm", "why": "x", "licence": "x"})
    with pytest.raises(ValueError, match="belongs"):
        demo_package.export_package(package)
    missing = "00000000-0000-0000-0000-000000000000"
    select(package, {"run": missing, "source": run.source.key, "why": "x", "licence": "x"})
    with pytest.raises(ValueError, match="absent"):
        demo_package.export_package(package)


def parcel_package(root):
    """One Onwani acquisition of a single Reem plot, as an exported package holds it."""
    feature = {
        "attributes": {
            "OBJECTID": 1,
            "DISTRICTENG": "AL REEM ISLAND",
            "MUNICIPALITYENG": "ADM",
            "SectorNumber_PlotID": "RT1_C1",
        },
        "geometry": {"rings": [[[54.4, 24.5], [54.41, 24.5], [54.4, 24.51], [54.4, 24.5]]]},
    }
    query = {
        "where": "DISTRICTENG = 'AL REEM ISLAND' AND MUNICIPALITYENG = 'ADM'",
        "returnIdsOnly": "true",
    }
    batch = {
        "where": query["where"],
        "objectIds": "1",
        "outFields": onwani.FIELDS,
        "returnGeometry": "true",
        "outSR": "4326",
    }
    metadata = {
        "name": "PLOT",
        "geometryType": "esriGeometryPolygon",
        "extent": {"spatialReference": {"wkid": 4326}},
        "fields": [{"name": f} for f in onwani.FIELDS.split(",")],
    }
    listing = {"objectIds": [1]}
    root.mkdir()
    (root / "blobs").mkdir()
    stamp = datetime(2026, 10, 1, tzinfo=UTC).isoformat()
    captures, provenance = [], []
    for value, suffix in (
        (metadata, "?f=pjson"),
        (listing, "/query?" + urlencode({"f": "json", **query})),
        (
            {"features": [feature], "spatialReference": {"wkid": 4326}},
            "/query?" + urlencode({"f": "json", **batch}),
        ),
        (listing, "/query?" + urlencode({"f": "json", **query})),
    ):
        payload = json.dumps(value).encode()
        digest = hashlib.sha256(payload).hexdigest()
        (root / "blobs" / digest).write_bytes(payload)
        receipt = {
            "url": onwani.BASE_URL + suffix,
            "fetched_at": stamp,
            "fetched_started_at": stamp,
            "http_status": 200,
            "acquisition_method": "scheduled_https_collect",
            "timestamp_basis": "collector_clock",
        }
        captures.append({"sha256": digest, "byte_length": len(payload), "receipt": receipt})
        if digest not in {row["sha256"] for row in provenance}:
            provenance.append(
                {
                    "sha256": digest,
                    "byte_length": len(payload),
                    "source": "dmt:onwani:smarthub:plot:adm:reem",
                    "run": "original",
                    "url": receipt["url"],
                    "http_status": 200,
                    "fetched_at": stamp,
                    "licence": LICENCE,
                }
            )
    manifest = {
        "version": archive.VERSION,
        "kind": "demo",
        "snapshot_at": stamp,
        "steps": [
            {
                "operation": "onwani",
                "scope": "al-reem-island",
                "run": "original",
                "original_status": "succeeded",
                "captures": captures,
            }
        ],
        "scenes": [],
        "tiles": [],
        "omitted": [],
    }
    archive.write_json(root / "manifest.json", manifest)
    archive.write_json(root / "provenance.json", provenance)
    return root


def test_load_rebuilds_rows_offline_and_writes_nothing_into_the_package(tmp_path, monkeypatch):
    package = parcel_package(tmp_path / "package")
    before = sorted(path.name for path in package.rglob("*"))
    monkeypatch.setattr(onwani, "fetch", lambda *a, **k: pytest.fail("network forbidden"))
    summary = demo_package.load_package(package, "ci-demo")
    assert summary == {"steps": 1, "projects": 0}
    assert Parcel.objects.get().geometry.valid
    assert sorted(path.name for path in package.rglob("*")) == before
    # A second load would merge into a populated database: refused.
    with pytest.raises(ValueError, match="empty"):
        demo_package.load_package(package, "ci-demo")


def test_load_refuses_undeclared_altered_or_unlicensed_bytes(tmp_path):
    package = parcel_package(tmp_path / "package")
    (package / "blobs" / ("0" * 64)).write_bytes(b"undeclared")
    with pytest.raises(ValueError, match="differ"):
        demo_package.load_package(package, "ci-demo")
    (package / "blobs" / ("0" * 64)).unlink()
    provenance = json.loads((package / "provenance.json").read_text())
    (package / "blobs" / provenance[0]["sha256"]).write_bytes(b"altered")
    with pytest.raises(ValueError, match="checksum"):
        demo_package.load_package(package, "ci-demo")
    package = parcel_package(tmp_path / "other")
    provenance = json.loads((package / "provenance.json").read_text())
    provenance[0]["licence"] = " "
    archive.write_json(package / "provenance.json", provenance)
    with pytest.raises(ValueError, match="licence"):
        demo_package.load_package(package, "ci-demo")
    assert not Capture.objects.exists()
