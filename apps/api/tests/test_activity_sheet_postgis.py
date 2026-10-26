"""Satellite ground-change signal on the project sheet, read from stored measurements (B07)."""

import os

import pytest
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("The activity signal reads stored measurements", allow_module_level=True)

from test_construction_activity_postgis import (  # noqa: E402
    MEASURED,
    finished_run,
    linked,  # noqa: F401
    reviewed,
    windows,
)

from property_platform.modules.evidence.projects import activity_import  # noqa: E402
from property_platform.modules.evidence.projects.activity_sheet import project_activity  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def measure(link, result=MEASURED):
    run = finished_run("sentinel-activity:al-reem-island")
    before, after = windows(run)
    activity_import.record_measurement(
        run=run, target=reviewed(link), before=before, after=after, result=result
    )


def test_a_project_without_measurement_lists_no_parcel(linked):  # noqa: F811
    sheet = project_activity(linked.project)
    assert sheet == {
        "source": {"name": "Copernicus Sentinel-2 L2A", "url": activity_import.SOURCE_URL},
        "parcels": [],
    }


def test_the_latest_measurement_is_a_level_and_never_a_share(linked):  # noqa: F811
    measure(linked)
    [parcel] = project_activity(linked.project)["parcels"]
    assert (parcel["source_record_id"], parcel["area_basis"]) == ("1", "reviewed_parcel")
    latest = parcel["latest"]
    assert (latest["status"], latest["level"], latest["clear_pixels"]) == ("measured", "high", 100)
    assert latest["before_acquired_at"] < latest["after_acquired_at"]
    assert latest["after_window"]["url"].startswith("https://sentinel-cogs.example/")
    assert parcel["area_m2"] == 11_000
    assert not {"changed_share", "changed_pixels", "median_difference"} & set(latest)


def test_an_unmeasurable_pair_is_said_without_a_level(linked):  # noqa: F811
    measure(
        linked,
        MEASURED
        | {
            "status": "insufficient_clear_pixels",
            "clear_pixels": 10,
            "changed_pixels": None,
            "changed_share": None,
            "median_difference": None,
            "level": None,
        },
    )
    [parcel] = project_activity(linked.project)["parcels"]
    assert (parcel["latest"]["status"], parcel["latest"]["level"]) == (
        "insufficient_clear_pixels",
        None,
    )


def test_a_revoked_link_hides_its_measurement(linked):  # noqa: F811
    measure(linked)
    linked.active, linked.revoked_at = False, timezone.now()
    linked.revoked_by, linked.revocation_reason = "integration-test", "Wrong plot"
    linked.save(update_fields=["active", "revoked_at", "revoked_by", "revocation_reason"])
    assert project_activity(linked.project)["parcels"] == []
