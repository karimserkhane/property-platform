"""Developer delivery history read from stored readings (B03)."""

import base64
import hashlib
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Delivery history reads stored project readings", allow_module_level=True)

from django.db import connection  # noqa: E402
from test_project_verification_postgis import adrec_receipt  # noqa: E402
from test_property_protocol import receipt  # noqa: E402

from property_platform.modules.evidence import project_protocol  # noqa: E402
from property_platform.modules.evidence.delivery_history import (  # noqa: E402
    developer_delivery_history,
)
from property_platform.modules.evidence.models import Capture, HistoryExclusion  # noqa: E402
from property_platform.modules.evidence.project_import import import_project_details  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

DEVELOPER = "reportage-properties"


def scope(source):
    return "saadiyat-island:sensi:" + hashlib.sha256(source["url"].encode()).hexdigest()


@pytest.fixture
def sensi():
    project = project_protocol.project_registry("saadiyat-island:sensi")[0]
    register = next(s for s in project["sources"] if s["parser"] == "adrec_project_v1")
    official = next(s for s in project["sources"] if s["parser"] == "official_project_v1")
    return register, official


def announce(official, fetched_at, handover):
    original = project_protocol.extract_project_source

    def extract(project, source, received):
        if source["parser"] != "official_project_v1":
            return original(project, source, received)
        return {
            "title": "Sensi",
            "parser_version": "fixture-extractor-v1",
            "summary": "",
            "handover": handover,
            "typologies": [],
            "amenities": [],
            "media": [],
        }

    row = receipt(official["url"], f"<html>{handover['original_text']}</html>".encode())
    row["fetched_at"] = row["fetched_started_at"] = fetched_at.isoformat()
    with patch.object(project_protocol, "extract_project_source", side_effect=extract):
        import_project_details([row], territory=scope(official), actor="delivery-test")


def read_register(register, fetched_at, status):
    row = adrec_receipt(
        register, progress=90 if status != "Completed" else 100, fetched_at=fetched_at
    )
    body = base64.b64decode(row["payload"]).replace(b'"Under Construction"', f'"{status}"'.encode())
    row["payload"] = base64.b64encode(body).decode()
    row["sha256"] = hashlib.sha256(body).hexdigest()
    import_project_details([row], territory=scope(register), actor="delivery-test")


def test_delivery_history_cites_each_announcement_and_register_reading(sensi, client):
    register, official = sensi
    now = datetime.now(UTC)
    announce(
        official,
        now - timedelta(days=400),
        {
            "precision": "year",
            "year": (now - timedelta(days=400)).year,
            "original_text": "Handover this year",
            "evidence_pointer": "Handover",
        },
    )
    announce(
        official,
        now - timedelta(days=200),
        {
            "precision": "quarter",
            "year": now.year + 1,
            "quarter": 1,
            "original_text": "Q1 next year",
            "evidence_pointer": "Handover",
        },
    )
    read_register(register, now - timedelta(days=30), "Under Construction")
    read_register(register, now - timedelta(days=1), "Completed")

    with CaptureQueriesContext(connection) as queries:
        history = developer_delivery_history(DEVELOPER)
    assert len(queries) <= 6
    assert all('"payload"' not in query["sql"] for query in queries)
    (project,) = history["projects"]
    assert project["slug"] == "sensi"
    first, second = project["announcements"]
    assert (first["change"], second["change"]) == ("first", "later")
    assert first["source"]["url"] == second["source"]["url"] == official["url"]
    # Unfinished in the register after the first announced year had ended.
    assert first["outcome"]["status"] == "late"
    assert first["outcome"]["late_by_at_least_days"] > 0
    assert first["outcome"]["source"]["kind"] == "authority"
    assert second["outcome"]["status"] == "met"
    assert [row["status"] for row in project["register_readings"]] == [
        "Under Construction",
        "Completed",
    ]
    assert project["completion"]["source"]["url"] == register["url"]
    assert history["summary"]["late_observed"] == history["summary"]["completed_observed"] == 1
    assert not {"actor", "receipt_key", "payload"} & project.keys()

    # A withdrawn announcement no longer counts.
    HistoryExclusion.objects.create(
        dataset="project:sensi",
        record_key=f"{official['url']}#handover",
        capture=Capture.objects.filter(url=official["url"]).latest("fetched_at"),
        actor="delivery-test",
        reason="Withdrawn claim",
    )
    assert developer_delivery_history(DEVELOPER)["projects"][0]["announcements"] == []

    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        url = f"/api/v1/preview/developers/{DEVELOPER}/delivery-history"
        response = client.get(url)
        assert response.status_code == 200
        assert response.json()["projects"][0]["register_readings"][1]["completed"] is True
        assert client.get("/api/v1/preview/developers/unknown/delivery-history").status_code == 404
        assert client.get("/api/v1/preview/developers/Bad_Key/delivery-history").status_code == 404
    with override_settings(DEBUG=False, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        assert client.get(url).status_code == 403
