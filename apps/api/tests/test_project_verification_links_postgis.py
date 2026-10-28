import os

import pytest
from django.db import IntegrityError, transaction

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Project verification links require real PostGIS", allow_module_level=True)

from property_platform.modules.catalog.models import Developer, Project  # noqa: E402
from property_platform.modules.evidence.models import ProjectVerificationLink  # noqa: E402
from property_platform.modules.evidence.projects import project_verification_links as sync  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

ACTOR = "integration-test"
PAGE = "https://www.dari.ae/en/app/directory/project/730"


def link(**changes):
    return {
        "project": "park-view",
        "registration_number": "2018/442116",
        "url": PAGE,
        "basis": "Directory page opened by the operator shows this project number.",
        "reviewed_on": "2026-10-24",
    } | changes


@pytest.fixture
def reviewed(monkeypatch):
    rows = [link(), link(project="not-imported-yet")]

    def registry(territory=None):
        return tuple(rows)

    monkeypatch.setattr(sync, "project_verification_links", registry)
    developer = Developer.objects.create(
        key="bloom", name="Bloom", website_url="https://example.com/"
    )
    Project.objects.create(
        slug="park-view",
        name="Park View",
        territory_id="saadiyat-island",
        developer=developer,
        website_url="https://example.com/park-view",
    )
    return rows


def test_links_follow_the_reviewed_file_and_wait_for_their_project(reviewed):
    summary = sync.apply_project_verification_links(actor=ACTOR)
    assert (summary["created"], summary["waiting"]) == (1, 1)
    active = ProjectVerificationLink.objects.get(active=True)
    assert (active.project.slug, active.registration_number, active.url, active.actor) == (
        "park-view",
        "2018/442116",
        PAGE,
        ACTOR,
    )
    again = sync.apply_project_verification_links(actor=ACTOR)
    assert (again["created"], again["kept"], again["revoked"]) == (0, 1, 0)


def test_a_revised_or_removed_link_is_revoked_not_deleted(reviewed):
    sync.apply_project_verification_links(actor=ACTOR)
    reviewed[0] = link(url="https://www.dari.ae/en/app/directory/project/731")
    revised = sync.apply_project_verification_links(actor=ACTOR)
    assert (revised["created"], revised["revoked"]) == (1, 1)
    old = ProjectVerificationLink.objects.get(active=False)
    assert (old.url, old.revoked_by) == (PAGE, ACTOR)
    assert old.revocation_reason.startswith("Superseded")
    reviewed.clear()
    removed = sync.apply_project_verification_links(actor=ACTOR)
    assert removed["revoked"] == 1
    assert ProjectVerificationLink.objects.filter(active=True).count() == 0
    assert ProjectVerificationLink.objects.count() == 2
    assert ProjectVerificationLink.objects.filter(revocation_reason=sync.REVOCATION_REASON).exists()


def test_a_territory_scope_leaves_other_territories_alone(reviewed):
    sync.apply_project_verification_links(actor=ACTOR)
    reviewed.clear()
    summary = sync.apply_project_verification_links(territory="al-reem-island", actor=ACTOR)
    assert summary["revoked"] == 0
    assert ProjectVerificationLink.objects.filter(active=True).count() == 1


def test_the_database_refuses_unofficial_pages_and_duplicate_active_links(reviewed):
    sync.apply_project_verification_links(actor=ACTOR)
    project = Project.objects.get(slug="park-view")
    values = {
        "project": project,
        "authority": "adrec",
        "registration_number": "2018/442116",
        "basis": "Second page.",
        "reviewed_on": "2026-10-24",
        "actor": ACTOR,
    }
    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectVerificationLink.objects.create(
            url="https://www.dari.ae/en/app/directory/project/999", **values
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectVerificationLink.objects.create(
            url="https://example.com/project/730", **values | {"registration_number": "2022/1"}
        )
