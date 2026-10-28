"""Recorded ADREC sales of a project on its sheet, by reviewed label (C01)."""

import os
from datetime import date

import pytest
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("The sales sheet reads stored ADREC snapshots", allow_module_level=True)

from test_adrec_postgis import execute, sales_acquisition  # noqa: E402
from test_adrec_protocol import sale  # noqa: E402

from property_platform.modules.catalog.models import Developer, Project  # noqa: E402
from property_platform.modules.evidence.models import ProjectMarketLabel  # noqa: E402
from property_platform.modules.evidence.projects.market_sheet import project_market  # noqa: E402
from property_platform.modules.evidence.sources import adrec  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

LATER = adrec.sales_scope("al-reem-island", as_of=date(2026, 10, 20))


@pytest.fixture
def project():
    developer = Developer.objects.create(
        key="developer", name="Developer", website_url="https://example.com/"
    )
    return Project.objects.create(
        slug="example-project",
        name="Example Project",
        territory_id="al-reem-island",
        developer=developer,
        website_url="https://example.com/example-project",
    )


@pytest.fixture
def labelled(project):
    return ProjectMarketLabel.objects.create(
        project=project,
        district="Al Reem Island",
        label="Example Project",
        evidence="project_name",
        basis="The ADREC sales label equals the registered project name.",
        reviewed_on=date(2026, 10, 26),
        actor="integration-test",
    )


def test_a_project_without_a_reviewed_label_has_no_sales_section(project):
    execute(sales_acquisition([sale()]))
    assert project_market(project) is None


def test_a_label_without_a_snapshot_says_so(labelled):
    sheet = project_market(labelled.project)
    assert (sheet["window"], sheet["groups"]) == (None, [])
    assert sheet["labels"][0]["label"] == "Example Project"


def test_only_the_newest_window_is_read_and_partial_shares_stay_out_of_ranges(labelled):
    execute(sales_acquisition([sale(), sale()]))
    cheaper = sale() | {"property_sale_price_aed": 1500000, "rate_aed_per_sqm": 15000}
    half = sale() | {"property_sale_price_aed": 900000, "property_sold_share": 0.5}
    other = sale() | {"project_name": "Another Project", "property_sale_price_aed": 10}
    studio = sale() | {"property_layout": "studio", "property_sale_price_aed": 800000}
    execute(sales_acquisition([sale(), cheaper, half, other, studio]), "later", scope=LATER)
    sheet = project_market(labelled.project)
    window = sheet["window"]
    assert (window["period_start"], window["period_end"]) == (date(2026, 7, 22), date(2026, 10, 19))
    assert window["captures"] and all(c["url"].startswith(adrec.SALES) for c in window["captures"])
    two_beds, studios = sheet["groups"]
    assert (two_beds["property_layout"], studios["property_layout"]) == ("2 beds", "studio")
    assert (two_beds["sales_count"], two_beds["full_share_count"]) == (3, 2)
    assert two_beds["price_aed"] == {"min": "1500000.00", "max": "1900000.12"}
    assert two_beds["rate_aed_per_sqm"]["min"] == "15000.00000000"
    assert (studios["sales_count"], studios["price_aed"]["min"]) == (1, "800000.00")
    assert two_beds["sale_sequence"] == "primary"


def test_a_revoked_label_hides_its_sales(labelled):
    execute(sales_acquisition([sale()]))
    labelled.active, labelled.revoked_at = False, timezone.now()
    labelled.revoked_by, labelled.revocation_reason = "integration-test", "Wrong project"
    labelled.save(update_fields=["active", "revoked_at", "revoked_by", "revocation_reason"])
    assert project_market(labelled.project) is None
