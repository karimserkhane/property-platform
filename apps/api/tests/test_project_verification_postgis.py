"""Register verification facts are stored per reading and keep their history (B02)."""

import base64
import hashlib
import json
import os
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Project verification storage requires PostGIS", allow_module_level=True)

from property_platform.modules.evidence.models import (  # noqa: E402
    ProjectSnapshot,
    ProjectVerification,
)
from property_platform.modules.evidence.project_import import import_project_details  # noqa: E402
from property_platform.modules.evidence.project_protocol import project_registry  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def adrec_receipt(source, *, progress, fetched_at):
    payload = json.dumps(
        {
            "Success": True,
            "Data": {
                "Result": {
                    "Id": int(source["record_id"]),
                    "Name": source["heading_aliases"][0],
                    "ProjectNumber": source["registration_number"],
                    "MunicipalityId": 1000,
                    "DistrictId": 2540,
                    "DistrictEn": "Al Saadiyat Island",
                    "DeveloperName": source["developer_aliases"][0],
                    "Status": "Under Construction",
                    "IsOffplan": True,
                    "ProgressPercentage": progress,
                    "InspectionDate": "/Date(1787256000000)/",
                    "SoldUnit": "0",
                    "EscrowBankName": "Test Bank",
                    "EscrowNumber": "000111",
                    "PropertyProjectUnits": [],
                }
            },
        }
    ).encode()
    return {
        "url": source["url"],
        "payload": base64.b64encode(payload).decode(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "http_status": 200,
        "fetched_at": fetched_at.isoformat(),
        "fetched_started_at": fetched_at.isoformat(),
    }


def test_each_register_reading_keeps_its_verification_and_history():
    project = project_registry("saadiyat-island:sensi")[0]
    source = next(s for s in project["sources"] if s["parser"] == "adrec_project_v1")
    scope = "saadiyat-island:sensi:" + hashlib.sha256(source["url"].encode()).hexdigest()
    earlier = timezone.now() - timedelta(days=30)
    first = adrec_receipt(source, progress=12.5, fetched_at=earlier)

    summary = import_project_details([first], territory=scope, actor="verification-test")
    assert summary["verifications"] == 1
    facts = ProjectVerification.objects.select_related("snapshot__capture").get()
    assert facts.registration_number == source["registration_number"]
    assert facts.progress_percent == Decimal("12.50")
    assert facts.progress_inspected_on == date(2026, 8, 21)
    assert facts.sold_percent is None and facts.sold_original == "0"
    assert facts.snapshot.source_kind == "authority"
    assert facts.snapshot.capture.fetched_at == earlier  # Observed then, measured on 21 Aug.

    # The same receipt is reused; it neither duplicates nor rewrites the facts.
    assert (
        import_project_details([first], territory=scope, actor="verification-test")["reused"] == 1
    )
    assert ProjectVerification.objects.count() == 1

    later = adrec_receipt(source, progress=20, fetched_at=timezone.now())
    import_project_details([later], territory=scope, actor="verification-test")
    history = list(
        ProjectVerification.objects.order_by("snapshot__capture__fetched_at").values_list(
            "progress_percent", flat=True
        )
    )
    assert history == [Decimal("12.50"), Decimal("20.00")]
    assert ProjectSnapshot.objects.filter(project__slug="sensi").count() == 2


def test_project_detail_reads_retention_at_the_latest_declared_progress(client):
    from django.test import override_settings

    project = project_registry("saadiyat-island:sensi")[0]
    source = next(s for s in project["sources"] if s["parser"] == "adrec_project_v1")
    scope = "saadiyat-island:sensi:" + hashlib.sha256(source["url"].encode()).hexdigest()
    earlier = adrec_receipt(source, progress=12.5, fetched_at=timezone.now() - timedelta(days=30))
    later = adrec_receipt(source, progress=30, fetched_at=timezone.now())
    for row in (earlier, later):
        import_project_details([row], territory=scope, actor="verification-test")

    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get("/api/v1/preview/projects/sensi")
    assert response.status_code == 200
    data = response.json()
    assert data["declared_progress"]["progress_percent"] == 30
    assert data["declared_progress"]["progress_inspected_on"] == "2026-08-21"
    assert data["declared_progress"]["source"]["kind"] == "authority"
    assert data["declared_progress"]["off_plan"] is True
    retention = data["cancellation_retention"]
    # 30 % is a boundary the cited commentaries leave open: both rates, never a guess.
    assert retention["status"] == "boundary" and retention["rates"] == [15, 25]
    assert retention["progress_inspected_on"] == "2026-08-21"
    assert retention["progress_source"]["url"] == source["url"]
    assert retention["paid_share_discretion_percent"] == 60
    assert retention["source"]["official_text_obtained"] is False
    assert retention["source"]["references"][0]["published_on"] == "2026-09-08"
