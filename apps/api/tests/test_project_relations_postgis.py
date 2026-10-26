import hashlib
import os
from datetime import UTC, datetime

import pytest
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Project relations require real PostGIS", allow_module_level=True)

from property_platform.modules.catalog.models import Developer, Project  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    HistoryExclusion,
    IngestionRun,
    ProjectRelation,
    ProjectSnapshot,
    Source,
)
from property_platform.modules.evidence.projects import project_relations as sync  # noqa: E402
from property_platform.modules.evidence.projects.project_queries import (  # noqa: E402
    project_detail,
    project_directory,
)

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

GATE_ARC = "https://www.aldar.com/properties/en/uae/reem-island/gate-arc"
GATE = "https://www.aldar.com/properties/en/uae/reem-island/gate"
ACTOR = "integration-test"


# Captures of the registered relations' review day (2026-10-23, UAE time) or earlier.
REVIEWED = datetime(2026, 10, 20, tzinfo=UTC)


def capture(url, fetched_at=REVIEWED):
    source, _ = Source.objects.get_or_create(
        key="test:projects", defaults={"name": "Test", "url": "https://example.com/"}
    )
    run = IngestionRun.objects.create(source=source, actor=ACTOR, connector_version="test")
    run.status, run.finished_at = "succeeded", timezone.now()
    run.save(update_fields=["status", "finished_at"])
    return Capture.objects.create(
        run=run,
        url=url,
        payload=b"<html></html>",
        byte_length=13,
        content_sha256=hashlib.sha256(f"{url}{fetched_at}".encode()).hexdigest(),
        http_status=200,
        fetched_at=fetched_at,
    )


def published(slug, name, evidence=None):
    developer, _ = Developer.objects.get_or_create(
        key="aldar-properties", defaults={"name": "Aldar", "website_url": "https://aldar.com/"}
    )
    project = Project.objects.create(
        slug=slug,
        name=name,
        territory_id="al-reem-island",
        developer=developer,
        website_url=f"https://example.com/{slug}",
    )
    evidence = evidence or capture(f"https://example.com/{slug}")
    ProjectSnapshot.objects.create(
        project=project,
        capture=evidence,
        receipt_key=hashlib.sha256(f"{slug}{evidence.pk}".encode()).hexdigest(),
        extractor_version="test",
        source_role="project",
        title=name,
        actor=ACTOR,
    )
    return project


@pytest.fixture
def gate():
    evidence = capture(GATE_ARC)
    return {
        "gate-arc": published("gate-arc", "Gate ARC", evidence),
        "gate": published("gate", "Gate", capture(GATE)),
        "the-arc": published("the-arc", "The ARC"),
        "the-gate-tower-1": published("the-gate-tower-1", "The Gate Tower 1"),
        "evidence": evidence,
    }


def test_relations_follow_the_registry_once_both_projects_and_evidence_exist(gate):
    summary = sync.apply_project_relations(territory="al-reem-island", actor=ACTOR)
    assert summary["created"] == 3
    assert summary["waiting"] > 0  # other registered components are not in this database
    links = {
        row.child.slug: (row.parent.slug, row.component, row.capture_id)
        for row in ProjectRelation.objects.filter(active=True)
    }
    assert links == {
        "gate": ("gate-arc", "The Gate Towers", gate["evidence"].pk),
        "the-arc": ("gate-arc", "The Arc Towers", gate["evidence"].pk),
        "the-gate-tower-1": ("gate", "Tower 1", gate["gate"].projectsnapshot_set.get().capture_id),
    }
    again = sync.apply_project_relations(territory="al-reem-island", actor=ACTOR)
    assert (again["created"], again["kept"], again["revoked"]) == (0, 3, 0)


def test_relation_evidence_is_the_page_as_reviewed_whatever_the_import_order(gate):
    # The page captured after the review day (UAE time) is never the cited evidence.
    capture(GATE_ARC, datetime(2026, 10, 23, 20, 30, tzinfo=UTC))
    sync.apply_project_relations(territory="al-reem-island", actor=ACTOR)
    relation = ProjectRelation.objects.get(child__slug="gate")
    assert relation.capture_id == gate["evidence"].pk
    # An archived capture of the review window imported later refines the citation in
    # place: the same relation, no revoked copy.
    later = capture(GATE_ARC, datetime(2026, 10, 23, 19, 0, tzinfo=UTC))
    summary = sync.apply_project_relations(territory="al-reem-island", actor=ACTOR)
    assert summary["created"] == summary["revoked"] == 0
    relation.refresh_from_db()
    assert relation.capture_id == later.pk and relation.active
    assert ProjectRelation.objects.filter(child__slug="gate").count() == 1


def test_a_relation_removed_from_the_registry_is_revoked_not_deleted(gate, monkeypatch):
    sync.apply_project_relations(territory="al-reem-island", actor=ACTOR)
    kept = [row for row in sync.project_relations("al-reem-island") if row["child"] != "the-arc"]
    monkeypatch.setattr(sync, "project_relations", lambda territory=None: tuple(kept))
    summary = sync.apply_project_relations(territory="al-reem-island", actor=ACTOR)
    assert summary["revoked"] == 1
    relation = ProjectRelation.objects.get(child__slug="the-arc")
    assert not relation.active
    assert relation.revocation_reason == sync.REVOCATION_REASON
    assert relation.revoked_by == ACTOR


def test_the_database_refuses_two_active_parents_and_self_links(gate):
    sync.apply_project_relations(territory="al-reem-island", actor=ACTOR)
    base = dict(
        kind="part_of",
        component="X",
        capture=gate["evidence"],
        basis="Test",
        reviewed_on="2026-10-23",
        actor=ACTOR,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectRelation.objects.create(child=gate["gate"], parent=gate["the-arc"], **base)
    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectRelation.objects.create(child=gate["the-arc"], parent=gate["the-arc"], **base)


def test_directory_and_dossier_show_parent_and_components_with_evidence(gate, client):
    sync.apply_project_relations(territory="al-reem-island", actor=ACTOR)
    items = {row["slug"]: row for row in project_directory("al-reem-island")["items"]}
    assert items["gate-arc"]["parent"] is None
    assert items["gate-arc"]["component_count"] == 2
    assert items["gate"]["parent"]["slug"] == "gate-arc"
    assert items["gate"]["component_count"] == 1
    detail = project_detail("gate")
    assert detail["parent"]["component"] == "The Gate Towers"
    assert detail["parent"]["source_url"] == GATE_ARC
    assert [row["slug"] for row in detail["components"]] == ["the-gate-tower-1"]
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get("/api/v1/preview/projects/gate-arc")
    assert response.status_code == 200
    assert {row["slug"] for row in response.json()["components"]} == {"gate", "the-arc"}


def test_an_unpublished_project_is_not_advertised_as_parent_or_component(gate):
    sync.apply_project_relations(territory="al-reem-island", actor=ACTOR)
    HistoryExclusion.objects.create(
        dataset="project:the-arc",
        record_key="https://example.com/the-arc",
        actor=ACTOR,
        reason="Source withdrawn in test",
        capture=gate["evidence"],
    )
    detail = project_detail("gate-arc")
    assert [row["slug"] for row in detail["components"]] == ["gate"]
