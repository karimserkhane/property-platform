"""Verification sheet on the project detail, read from stored readings (B05)."""

import os
from datetime import UTC, datetime, timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("The verification sheet reads stored project readings", allow_module_level=True)

from test_delivery_history_postgis import announce, read_register, sensi  # noqa: E402, F401

from property_platform.modules.catalog.models import Project  # noqa: E402
from property_platform.modules.evidence.models import ProjectVerificationLink  # noqa: E402
from property_platform.modules.evidence.projects.project_queries import project_detail  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def test_project_detail_carries_register_facts_links_and_contradictions(sensi, client):  # noqa: F811
    register, official = sensi
    now = datetime.now(UTC)
    read_register(register, now - timedelta(days=30), "Under Construction")
    read_register(register, now - timedelta(days=10), "Completed")
    # The developer page still announces a later year after the register stated completion.
    announce(
        official,
        now - timedelta(days=2),
        {
            "precision": "year",
            "year": now.year + 2,
            "original_text": "Handover in two years",
            "evidence_pointer": "Handover",
        },
    )

    sheet = project_detail("sensi")["verification"]
    facts = sheet["latest_reading"]
    assert facts["registration_number"] == register["registration_number"]
    assert facts["register_status"] == "Completed"
    assert facts["escrow_bank_name"] == "Test Bank"
    assert facts["escrow_account_number"] == "000111"
    assert facts["source"]["url"] == register["url"]
    assert [row["status"] for row in sheet["register_readings"]] == [
        "Under Construction",
        "Completed",
    ]
    assert sheet["completion"]["source"]["url"] == register["url"]
    (contradiction,) = sheet["contradictions"]
    assert contradiction["code"] == "announced_after_completion"
    assert contradiction["announcements"][0]["source"]["url"] == official["url"]
    assert sheet["official_links"] == []

    project = Project.objects.get(slug="sensi")
    url = "https://www.dari.ae/en/app/directory/project/123"
    ProjectVerificationLink.objects.create(
        project=project,
        authority="adrec",
        registration_number=register["registration_number"],
        url=url,
        basis="Fixture review",
        reviewed_on=now.date(),
        actor="verification-test",
    )
    revoked = ProjectVerificationLink.objects.create(
        project=project,
        authority="adrec",
        registration_number="2018/000001",
        url="https://www.dari.ae/en/app/directory/project/124",
        basis="Fixture review",
        reviewed_on=now.date(),
        actor="verification-test",
    )
    ProjectVerificationLink.objects.filter(pk=revoked.pk).update(
        active=False,
        revoked_at=timezone.now(),
        revoked_by="verification-test",
        revocation_reason="Wrong page",
    )
    (link,) = project_detail("sensi")["verification"]["official_links"]
    assert link["url"] == url
    assert "basis" not in link and "actor" not in link

    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get("/api/v1/preview/projects/sensi")
        assert response.status_code == 200
        body = response.json()["verification"]
        assert body["latest_reading"]["register_status"] == "Completed"
        assert body["contradictions"][0]["code"] == "announced_after_completion"
        assert body["official_links"][0]["reviewed_on"] == now.date().isoformat()
