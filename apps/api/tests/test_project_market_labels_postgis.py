import os

import pytest
from django.db import IntegrityError, transaction

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Project market labels require real PostGIS", allow_module_level=True)

from property_platform.modules.catalog.models import Developer, Project  # noqa: E402
from property_platform.modules.evidence.models import ProjectMarketLabel  # noqa: E402
from property_platform.modules.evidence.projects import project_market_labels as sync  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

ACTOR = "integration-test"


def label(**changes):
    return {
        "project": "flow-25",
        "district": "Al Reem Island",
        "label": "Flow25",
        "evidence": "project_name",
        "basis": "The ADREC sales label equals the registered project name.",
        "reviewed_on": "2026-10-26",
    } | changes


@pytest.fixture
def reviewed(monkeypatch):
    rows = [label(), label(project="not-imported-yet", label="Elsewhere")]

    def registry(territory=None):
        return tuple(rows)

    monkeypatch.setattr(sync, "project_market_labels", registry)
    developer = Developer.objects.create(
        key="developer", name="Developer", website_url="https://example.com/"
    )
    for slug, name in (("flow-25", "Flow 25"), ("other", "Other")):
        Project.objects.create(
            slug=slug,
            name=name,
            territory_id="al-reem-island",
            developer=developer,
            website_url=f"https://example.com/{slug}",
        )
    return rows


def test_labels_follow_the_reviewed_file_and_wait_for_their_project(reviewed):
    summary = sync.apply_project_market_labels(actor=ACTOR)
    assert (summary["created"], summary["waiting"]) == (1, 1)
    active = ProjectMarketLabel.objects.get(active=True)
    assert (active.project.slug, active.district, active.label, active.actor) == (
        "flow-25",
        "Al Reem Island",
        "Flow25",
        ACTOR,
    )
    again = sync.apply_project_market_labels(actor=ACTOR)
    assert (again["created"], again["kept"], again["revoked"]) == (0, 1, 0)


def test_a_relinked_or_removed_label_is_revoked_not_deleted(reviewed):
    sync.apply_project_market_labels(actor=ACTOR)
    reviewed[0] = label(project="other", basis="Reviewed again: the label names Other.")
    revised = sync.apply_project_market_labels(actor=ACTOR)
    assert (revised["created"], revised["revoked"]) == (1, 1)
    old = ProjectMarketLabel.objects.get(active=False)
    assert (old.project.slug, old.revoked_by) == ("flow-25", ACTOR)
    assert old.revocation_reason.startswith("Superseded")
    assert ProjectMarketLabel.objects.get(active=True).project.slug == "other"
    reviewed.clear()
    removed = sync.apply_project_market_labels(actor=ACTOR)
    assert removed["revoked"] == 1
    assert ProjectMarketLabel.objects.filter(active=True).count() == 0
    assert ProjectMarketLabel.objects.count() == 2
    assert ProjectMarketLabel.objects.filter(revocation_reason=sync.REVOCATION_REASON).exists()


def test_a_territory_scope_leaves_other_territories_alone(reviewed):
    sync.apply_project_market_labels(actor=ACTOR)
    reviewed.clear()
    summary = sync.apply_project_market_labels(territory="saadiyat-island", actor=ACTOR)
    assert summary["revoked"] == 0
    assert ProjectMarketLabel.objects.filter(active=True).count() == 1


def test_the_database_refuses_unreviewed_or_duplicate_active_labels(reviewed):
    sync.apply_project_market_labels(actor=ACTOR)
    values = {
        "project": Project.objects.get(slug="other"),
        "district": "Al Reem Island",
        "basis": "Second link.",
        "reviewed_on": "2026-10-26",
        "actor": ACTOR,
    }
    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectMarketLabel.objects.create(label="Flow25", evidence="project_name", **values)
    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectMarketLabel.objects.create(label="Other", evidence="register_name", **values)
    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectMarketLabel.objects.create(label="Other", evidence="fuzzy", **values)
