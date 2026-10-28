"""Published state of the rebuild check on real PostGIS (owner decision of 2026-10-24)."""

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Published state comparison requires real PostGIS", allow_module_level=True)

from django.contrib.gis.geos import MultiPolygon, Polygon  # noqa: E402

from property_platform.modules.catalog.models import Building, Developer, Project  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    IngestionRun,
    ProjectIdentityLink,
    ProjectSnapshot,
    ProjectTypology,
    Source,
)
from property_platform.modules.evidence.projects.project_import import revoke_project_link  # noqa: E402
from property_platform.modules.evidence.projects.project_queries import project_detail  # noqa: E402
from property_platform.modules.evidence.rebuild import rebuild_archive as archive  # noqa: E402
from property_platform.modules.evidence.rebuild import rebuild_published as published  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

ACTOR = "integration-test"
URL = "https://example.com/tower"
FETCHED = datetime(2026, 10, 1, tzinfo=UTC)


def tower():
    developer = Developer.objects.create(
        key="test-developer", name="Test Developer", website_url="https://example.com/"
    )
    return Project.objects.create(
        slug="tower",
        name="Tower",
        territory_id="al-reem-island",
        developer=developer,
        website_url=URL,
    )


def reading(project, *, version, summary="", typologies=(), fetched_at=FETCHED, payload=None):
    """One reading of a receipt; reading the same bytes again creates a new capture row."""
    payload = payload or b"<html>Tower page</html>"
    source, _ = Source.objects.get_or_create(
        key="test:projects", defaults={"name": "Test", "url": "https://example.com/"}
    )
    run = IngestionRun.objects.create(source=source, actor=ACTOR, connector_version="test")
    run.status, run.finished_at = "succeeded", timezone.now()
    run.save(update_fields=["status", "finished_at"])
    capture = Capture.objects.create(
        run=run,
        url=URL,
        payload=payload,
        byte_length=len(payload),
        content_sha256=hashlib.sha256(payload).hexdigest(),
        http_status=200,
        fetched_at=fetched_at,
    )
    snapshot = ProjectSnapshot.objects.create(
        project=project,
        capture=capture,
        receipt_key=hashlib.sha256(f"{capture.pk}:{version}".encode()).hexdigest(),
        extractor_version=version,
        source_role="project",
        title=project.name,
        summary=summary,
        actor=ACTOR,
    )
    for property_type, bedrooms in typologies:
        ProjectTypology.objects.create(
            snapshot=snapshot,
            property_type=property_type,
            bedrooms=bedrooms,
            original_text=property_type,
            evidence_pointer="Unit types",
        )
    return snapshot


def building(record_id):
    return Building.objects.create(
        source_namespace="osm:test",
        source_record_id=record_id,
        name="Provider building",
        geometry=MultiPolygon(Polygon.from_bbox((54.4, 24.49, 54.401, 24.491)), srid=4326),
    )


def test_a_newer_reading_of_the_same_receipt_replaces_the_older_one():
    project = tower()
    reading(project, version="v1", summary="Old reading", typologies=[("studio", 0)])
    reading(project, version="v2", summary="Current reading")
    detail = project_detail("tower")
    # The current interpretation of the same bytes is published; nothing is deleted.
    assert detail["summary"] == "Current reading" and detail["typologies"] == []
    assert ProjectSnapshot.objects.count() == 2 and ProjectTypology.objects.count() == 1
    # A later, different receipt without the fact still cannot hide it.
    reading(project, version="v2", fetched_at=FETCHED + timedelta(days=1), payload=b"<html/>")
    assert project_detail("tower")["summary"] == "Current reading"


def test_published_state_uses_durable_identities_and_lists_operator_decisions():
    project = tower()
    evidence = reading(project, version="v2", summary="Current reading").capture
    kept, revoked = (
        ProjectIdentityLink.objects.create(
            project=project, capture=evidence, actor=ACTOR, reason="Reviewed", building=building(r)
        )
        for r in ("1", "2")
    )
    revoke_project_link(revoked.pk, actor="Karim", reason="Position withdrawn")
    state = published.published_state()
    assert list(state["projects"]) == ["tower"]
    dossier = json.dumps(state["projects"]["tower"])
    assert str(project.pk) not in dossier and str(kept.building_id) not in dossier
    assert state["projects"]["tower"]["summary"] == "Current reading"
    assert state["identity_links"] == [
        {
            "project": "tower",
            "target": "building",
            "namespace": "osm:test",
            "record_id": "1",
            "reason": "Reviewed",
        }
    ]
    assert state["decisions"] == {"tower": ["link_revocation"]}


def manifest(path, **values):
    archive.write_json(
        path / "manifest.json",
        {
            "version": 1,
            "snapshot_at": "2026-10-24T00:00:00+00:00",
            "steps": [],
            "scenes": [],
            "tiles": [],
            "omitted": [],
        }
        | values,
    )


def test_published_state_blocks_and_reading_history_is_an_alert(tmp_path):
    project = tower()
    reading(project, version="v2", summary="Current reading", typologies=[("studio", 0)])
    expected = archive.counts()
    # The original database also held an earlier reading of the same receipt.
    expected["evidence.project_snapshot"] += 1
    state = published.published_state()
    manifest(
        tmp_path, expected=expected, published=state, interpretations=published.interpretations()
    )
    result = archive.replay_archive(tmp_path, "integration-rebuild", str(uuid4()))
    report = json.loads((tmp_path / "report.json").read_text())
    assert result["ok"], report["published"]
    assert result["history_differences"] == ["evidence.project_snapshot"]
    assert result["published_blocking"] == 0 and not result["mismatches"]
    table = next(r for r in report["tables"] if r["table"] == "evidence.project_snapshot")
    assert table["policy"] == "history" and not table["matches"]
    assert report["interpretations"]["actual"]["readings_by_extractor"] == {
        "v2": {"readings": 1, "receipts": 1}
    }
    # A published fact the rebuild does not reproduce fails the check.
    state["projects"]["tower"]["summary"] = "A fact only the original database had"
    manifest(tmp_path, expected=expected, published=state)
    result = archive.replay_archive(tmp_path, "integration-rebuild", str(uuid4()))
    assert not result["ok"] and result["published_blocking"] == 1


def test_a_manifest_without_published_state_keeps_history_tables_exact(tmp_path):
    reading(tower(), version="v2", summary="Current reading")
    expected = archive.counts()
    expected["evidence.project_snapshot"] += 1
    manifest(tmp_path, expected=expected)
    result = archive.replay_archive(tmp_path, "integration-rebuild", str(uuid4()))
    assert not result["ok"] and result["published_blocking"] is None
    assert result["mismatches"] == ["evidence.project_snapshot"]


def test_the_search_index_is_rebuilt_last_and_never_blocks(tmp_path):
    reading(tower(), version="v2", summary="Current reading", typologies=[("studio", 0)])
    expected = archive.counts()
    manifest(tmp_path, expected=expected, published=published.published_state())
    result = archive.replay_archive(tmp_path, "integration-rebuild", str(uuid4()))
    report = json.loads((tmp_path / "report.json").read_text())
    table = next(r for r in report["tables"] if r["table"] == "evidence.evidence_search_entry")
    assert table["policy"] == "derived" and table["actual"] > table["expected"] == 0
    assert "evidence.evidence_search_entry" not in result["mismatches"]
    assert not any(step["operation"] == "evidence_search" for step in report["steps"])
