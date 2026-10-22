import hashlib
import json
import os
from datetime import UTC, datetime
from unittest.mock import Mock
from urllib.parse import urlencode

import pytest
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("ADREC materialisation requires real PostgreSQL", allow_module_level=True)

from test_adrec_protocol import SCOPE, index, page, sale  # noqa: E402

from property_platform.modules.evidence import adrec  # noqa: E402
from property_platform.modules.evidence.models import (
    AdrecMarketSnapshot,
    AdrecSaleObservation,
    Capture,
)  # noqa: E402
from property_platform.modules.evidence.orchestration import (
    execute_import,
    record_acquisition_failure,
)  # noqa: E402
from property_platform.modules.publication.adrec_preview import market  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def receipt(payload, url=adrec.SALES, params=None):
    now = datetime.now(UTC)
    return payload, {
        "url": url + "?" + urlencode(params or adrec.sales_params(SCOPE)),
        "http_status": 200,
        "fetched_started_at": now,
        "fetched_at": now,
        "etag": "",
        "last_modified_raw": "",
        "acquisition_method": "scheduled_https_collect",
        "timestamp_basis": "collector_clock",
    }


def sales_acquisition(rows, *, drift=False):
    visits = {}

    def acquire(url, params):
        window = (params["fromDate"], params["toDate"])
        visits[window] = visits.get(window, 0) + 1
        selected = [
            row for row in rows if window[0] <= row["sale_application_datetime"] <= window[1]
        ]
        if drift and selected and visits[window] == 2:
            selected = [{**row, "project_name": "Changed"} for row in selected]
        return receipt(page(selected), url, params)

    return Mock(side_effect=acquire)


def execute(acquire, identity="first", operation="adrec_sales", scope=SCOPE):
    return execute_import(
        operation=operation,
        scope=scope,
        actor="test-adrec",
        execution_key=hashlib.sha256(identity.encode()).hexdigest(),
        acquisition=acquire,
    )


def test_snapshots_preserve_multiplicity_retry_is_noop_and_latest_is_only_counted():
    acquire = sales_acquisition([sale(), sale()])
    first = execute(acquire)
    assert first["status"] == "succeeded"
    assert execute(acquire)["reused"] and acquire.call_count == 6
    assert AdrecSaleObservation.objects.count() == 2
    execute(sales_acquisition([sale()]), "second")
    assert AdrecMarketSnapshot.objects.count() == 2
    assert AdrecSaleObservation.objects.count() == 3
    assert market("al-reem-island")["total"] == 1
    assert market("saadiyat-island")["total"] == 0
    assert market("al-reem-island", query="absent")["total"] == 0
    previous = AdrecMarketSnapshot.objects.order_by("created_at").first()
    archived = market("al-reem-island", snapshot_id=previous.pk)
    assert archived["historical"] and archived["total"] == 2
    assert len(archived["snapshots"]) == 2
    row = AdrecSaleObservation.objects.first()
    assert row.capture.run_id == row.snapshot.run_id and row.field_path == "content[0]"


def test_changed_snapshot_preserves_evidence_and_previous_complete_snapshot():
    execute(sales_acquisition([sale()]))
    acquire = sales_acquisition([sale()], drift=True)
    assert execute(acquire, "failure")["status"] == "failed"
    assert AdrecMarketSnapshot.objects.count() == 1 and Capture.objects.count() == 12
    assert market("al-reem-island")["sales"][0]["project_name"] == "Example Project"


def test_indices_capture_ambiguous_series_but_publish_only_usable_values():
    acquire = Mock(
        side_effect=[
            receipt(json.dumps([index()]).encode(), adrec.INDICES["sale"], adrec.index_params()),
            receipt(
                json.dumps([index(100), index(110)]).encode(),
                adrec.INDICES["rent"],
                adrec.index_params(),
            ),
        ]
    )
    result = execute(acquire, operation="adrec_indices", scope="abu-dhabi")
    assert result["status"] == "quarantined"
    snapshot = AdrecMarketSnapshot.objects.get()
    assert snapshot.indices.filter(usable=False).count() == 2
    output = market("saadiyat-island")
    assert output["index_review_needed"] and len(output["indices"]) == 1
    assert output["indices"][0]["kind"] == "sale"


def test_failed_precollection_journals_received_adrec_response():
    payload, proof = receipt(page([sale()]))
    result = record_acquisition_failure(
        operation="adrec_sales",
        scope=SCOPE,
        actor="test-adrec",
        execution_key="f" * 64,
        error=adrec.AdrecError("drift"),
        received_acquisitions=[{"payload": payload, "receipt": proof}],
    )
    assert result["status"] == "failed" and Capture.objects.get().payload == payload
    assert not AdrecMarketSnapshot.objects.exists()


@override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True)
def test_endpoint_is_bounded_and_serializes_decimal_as_strings(client):
    execute(sales_acquisition([sale()]))
    url = "/api/v1/preview/adrec-market"
    response = client.get(url, {"territory": "al-reem-island"})
    assert response.status_code == 200 and response.json()["sales"][0]["price_aed"] == "1900000.12"
    assert client.get(url, {"territory": "dubai"}).status_code == 422
    assert client.get(url, {"territory": "al-reem-island", "limit": 101}).status_code == 422
    with override_settings(PROPERTY_PLATFORM_PARCEL_PREVIEW=False, DEBUG=False):
        assert client.get(url, {"territory": "al-reem-island"}).status_code == 403
