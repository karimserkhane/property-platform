"""Withdrawn sites stay in history but never reach a published read (A19)."""

import hashlib
import itertools
import os
from datetime import UTC, date, datetime

import pytest
from django.contrib.gis.geos import Point
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Withdrawal filters require real PostGIS", allow_module_level=True)

from property_platform.modules.catalog.models import Developer, Place, Project  # noqa: E402
from property_platform.modules.evidence import source_withdrawals  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    IngestionRun,
    ProjectIdentityLink,
    ProjectRelation,
    ProjectSnapshot,
    PropertyPresentation,
    ResearchReference,
    Source,
)
from property_platform.modules.evidence.projects.project_queries import (  # noqa: E402
    project_detail,
    project_directory,
    published_slugs,
)
from property_platform.modules.evidence.projects.queries import (  # noqa: E402
    property_presentations,
    research_references,
)

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

ACTOR = "withdrawal-test"
DEVELOPER = "https://tigerproperties.ae/"
DEVELOPER_PAGE = "https://tigerproperties.ae/renad-tower/"
PSI_PAGE = "https://psinv.net/en/projects/abu-dhabi/abu-dhabi-district/al-reem-island/renad-tower-1"
ALDAR_PAGE = "https://www.aldar.com/properties/en/uae/reem-island/gate"
REDDIT_PAGE = "https://www.reddit.com/r/AbuDhabi_Real_Estate/comments/x/"
SERIAL = itertools.count()


def capture(url):
    source, _ = Source.objects.get_or_create(
        key=f"test:{hashlib.sha256(url.encode()).hexdigest()[:40]}",
        defaults={"name": "Test", "url": url},
    )
    run = IngestionRun.objects.create(source=source, actor=ACTOR, connector_version="test")
    run.status, run.finished_at = "succeeded", timezone.now()
    run.save(update_fields=["status", "finished_at"])
    return Capture.objects.create(
        run=run,
        url=url,
        payload=b"<html></html>",
        byte_length=13,
        content_sha256=hashlib.sha256(f"{url}{next(SERIAL)}".encode()).hexdigest(),
        http_status=200,
        fetched_at=datetime(2026, 10, 20, tzinfo=UTC),
    )


def project(slug, website_url=""):
    developer, _ = Developer.objects.get_or_create(
        key="tiger-properties", defaults={"name": "Tiger Properties", "website_url": DEVELOPER}
    )
    return Project.objects.create(
        slug=slug,
        name=slug.replace("-", " ").title(),
        territory_id="al-reem-island",
        developer=developer,
        website_url=website_url or f"{DEVELOPER}{slug}/",
    )


def snapshot(owner, url, **facts):
    return ProjectSnapshot.objects.create(
        project=owner,
        capture=capture(url),
        receipt_key=hashlib.sha256(f"{owner.slug}{url}{next(SERIAL)}".encode()).hexdigest(),
        extractor_version="test",
        source_role="project",
        title=owner.name,
        actor=ACTOR,
        **facts,
    )


def place(name, namespace, kind="publisher_project_marker"):
    return Place.objects.create(
        source_namespace=namespace,
        source_record_id="publisher-map",
        name=name,
        kind=kind,
        geometry=Point(54.394, 24.5003, srid=4326),
    )


@pytest.fixture
def catalogue():
    renad = project("renad-tower", website_url=PSI_PAGE)
    snapshot(renad, DEVELOPER_PAGE, source_kind="developer", source_name="Tiger Properties")
    snapshot(
        renad,
        PSI_PAGE,
        source_kind="broker",
        source_name="Property Shop Investment (PSI)",
        handover_precision="year",
        handover_year=2027,
        handover_original="2027",
        handover_pointer="fixture:handover",
    )
    ProjectIdentityLink.objects.create(
        project=renad,
        place=place("Renad Tower", "project:renad-tower:broker:psi"),
        capture=capture(PSI_PAGE),
        actor=ACTOR,
        reason="Agency point",
    )
    snapshot(project("sky-tower"), PSI_PAGE.replace("renad-tower-1", "sky-tower-2"))
    gate = project("gate")
    snapshot(gate, f"{DEVELOPER}gate/", source_kind="developer")
    ProjectRelation.objects.create(
        child=renad,
        parent=gate,
        kind="part_of",
        component="Tower",
        capture=capture(ALDAR_PAGE),
        basis="Listed on the programme page",
        reviewed_on=date(2026, 10, 23),
        actor=ACTOR,
    )
    building = place("Gate Tower", "osm:test", kind="residential")
    PropertyPresentation.objects.create(
        place=building,
        capture=capture(ALDAR_PAGE),
        display_name="Gate Tower",
        publisher_name="Aldar Properties",
        website_url=ALDAR_PAGE,
        summary="A tower of the Gate programme.",
        review_version="test",
    )
    ResearchReference.objects.create(
        capture=capture(REDDIT_PAGE),
        label="Forum thread",
        source_kind="forum",
        available=True,
        mapping_version="test",
    )
    return building


def test_withdrawn_sites_leave_no_fact_pin_link_or_project_behind(catalogue):
    assert published_slugs() == ["gate", "renad-tower"]
    renad = project_detail("renad-tower")
    assert renad["handover"] is None
    assert [source["url"] for source in renad["sources"]] == [DEVELOPER_PAGE]
    assert renad["map_locations"] == []
    assert renad["parent"] is None
    # An agency page is never shown as the project's site, withdrawn or not.
    assert renad["website_url"] == DEVELOPER_PAGE
    assert project_detail("sky-tower") is None
    items = {row["slug"]: row for row in project_directory()["items"]}
    assert not items["renad-tower"]["has_map_identity"]
    assert items["renad-tower"]["website_url"] == DEVELOPER
    assert items["renad-tower"]["parent"] is None
    assert property_presentations("place", [catalogue.id]) == {}
    assert research_references() == []


def test_removing_a_decision_restores_every_read_without_rewriting_history(catalogue, monkeypatch):
    rows = ProjectSnapshot.objects.count()
    monkeypatch.setattr(source_withdrawals, "withdrawals", lambda: ())
    assert published_slugs() == ["gate", "renad-tower", "sky-tower"]
    renad = project_detail("renad-tower")
    assert renad["handover"]["year"] == 2027
    assert len(renad["map_locations"]) == 1
    assert renad["parent"]["slug"] == "gate"
    assert property_presentations("place", [catalogue.id])[str(catalogue.id)]["website_url"] == (
        ALDAR_PAGE
    )
    assert [row["url"] for row in research_references()] == [REDDIT_PAGE]
    assert ProjectSnapshot.objects.count() == rows


def test_presentations_replay_withdrawn_receipts_and_skip_them_once_collection_stops():
    from test_property_presentations_postgis import sample

    from property_platform.modules.evidence.projects.property_import import import_presentations

    building, row, photo, receipts = sample()
    assert source_withdrawals.is_withdrawn(row["source_url"])
    # An archived batch still holding the withdrawn page replays exactly as recorded.
    import_presentations(receipts, actor=ACTOR, profiles=[row], photos={"example": photo})
    assert PropertyPresentation.objects.count() == 1
    # A new batch no longer contains it; the profile is skipped instead of failing.
    import_presentations([], actor=ACTOR, profiles=[row], photos={"example": photo})
    assert PropertyPresentation.objects.count() == 1
    assert property_presentations("building", [building.id]) == {}


def test_plain_links_to_a_withdrawn_site_follow_its_decision(catalogue):
    gate = project_detail("gate")
    Project.objects.filter(slug="gate").update(website_url=ALDAR_PAGE)
    assert project_detail("gate")["website_url"] == ALDAR_PAGE  # links remain allowed
    Project.objects.filter(slug="gate").update(website_url=PSI_PAGE)
    assert project_detail("gate")["website_url"] == f"{DEVELOPER}gate/"
    assert gate["developer"]["website_url"] == DEVELOPER
