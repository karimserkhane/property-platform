import hashlib
import json
import os
from datetime import UTC, datetime

import pytest
from django.contrib.gis.geos import Point
from django.db import IntegrityError, transaction
from django.test import override_settings

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Public context needs real PostGIS", allow_module_level=True)

from test_public_context_protocol import district, facility, school_archive  # noqa: E402

from property_platform.modules.evidence import abu_dhabi  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    HealthFacilityObservation,
    PublicContextSnapshot,
)
from property_platform.modules.evidence.orchestration import (  # noqa: E402
    execute_import,
    record_acquisition_failure,
)
from property_platform.modules.publication.context_preview import public_context  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def acquired(rows, status=200):
    now = datetime.now(UTC)
    return json.dumps(rows).encode(), {
        "url": abu_dhabi.FEEDS["health"].url,
        "http_status": status,
        "fetched_started_at": now,
        "fetched_at": now,
        "etag": "",
        "last_modified_raw": "",
        "acquisition_method": "scheduled_https_collect",
        "timestamp_basis": "collector_clock",
    }


def execute(rows, identity="one", completion_check=None):
    return execute_import(
        operation="public_context",
        scope="abu-dhabi:health",
        actor="test-context",
        execution_key=hashlib.sha256(identity.encode()).hexdigest(),
        acquisition=lambda url, params: acquired(rows),
        completion_check=completion_check,
    )


def test_append_snapshots_retry_noop_and_paging_only_latest_snapshot():
    first = execute([facility(), facility(62, FacilityName="Second")])
    assert first["status"] == "succeeded" and execute([facility()])["reused"]
    assert HealthFacilityObservation.objects.count() == 2
    execute([facility(), facility(62, FacilityName="Changed")], "next")
    assert (
        PublicContextSnapshot.objects.count() == 2
        and HealthFacilityObservation.objects.count() == 4
    )
    data = public_context("health", limit=1)
    assert data["total"] == 2 and data["has_more"] and len(data["health"]) == 1
    assert public_context("health", query="Changed")["total"] == 1
    row = HealthFacilityObservation.objects.first()
    assert row.location.srid == 4326 and row.snapshot.capture.run_id == row.snapshot.run_id
    assert row.snapshot.source_modified_date is None


def test_invalid_batch_or_sudden_coverage_loss_cannot_replace_last_snapshot():
    execute([facility(i) for i in range(1, 6)])
    assert execute([facility()], "partial")["status"] == "failed"
    assert execute([facility(Longitude=0)], "invalid")["status"] == "failed"
    assert PublicContextSnapshot.objects.count() == 1 and Capture.objects.count() == 3
    assert public_context("health")["total"] == 5


def test_sql_rejects_empty_or_out_of_bounds_points_and_duplicate_identity():
    execute([facility()])
    row = HealthFacilityObservation.objects.get()
    for location in [Point(0, 0, srid=4326), Point(srid=4326)]:
        with pytest.raises(IntegrityError), transaction.atomic():
            HealthFacilityObservation.objects.filter(pk=row.pk).update(location=location)
    with pytest.raises(IntegrityError), transaction.atomic():
        row.pk = None
        row.save()


def test_mismatched_replay_rolls_back_writes_and_can_retry():
    def wrong():
        raise ValueError("unconsumed response")

    assert execute([facility()], completion_check=wrong)["status"] == "failed"
    assert not PublicContextSnapshot.objects.exists()
    assert execute([facility()])["status"] == "succeeded"


def test_failed_acquisition_preserves_http_response_without_inventing_snapshot():
    payload, receipt = acquired({}, status=401)
    result = record_acquisition_failure(
        operation="public_context",
        scope="abu-dhabi:health",
        actor="test-context",
        execution_key="d" * 64,
        error=abu_dhabi.ContextError("source unavailable"),
        received_acquisitions=[{"payload": payload, "receipt": receipt}],
    )
    assert result["status"] == "failed" and Capture.objects.get().http_status == 401
    assert not PublicContextSnapshot.objects.exists()


def test_http_preview_guard_and_validation(client):
    with override_settings(DEBUG=False):
        assert client.get("/api/v1/preview/public-context?dataset=health").status_code == 403
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        execute([facility()])
        assert (
            client.get("/api/v1/preview/public-context?dataset=health&territory=dubai").status_code
            == 422
        )
        result = client.get(
            "/api/v1/preview/public-context?dataset=health&territory=saadiyat-island"
        )
        assert result.status_code == 200 and result.json()["territory"] == "abu-dhabi"


def test_district_topology_and_capture_chain_preserve_provider_identity():
    body = json.dumps({"type": "FeatureCollection", "features": [district()]}).encode()
    ids = json.dumps({"objectIds": [1]}).encode()

    def acquire(url, params):
        _, receipt = acquired([])
        receipt["url"] = url
        return ids if url == abu_dhabi.DISTRICT_IDS else body, receipt

    result = execute_import(
        operation="public_context",
        scope="abu-dhabi:districts",
        actor="test-district",
        execution_key="e" * 64,
        acquisition=acquire,
    )
    assert result["status"] == "succeeded"
    snapshot = PublicContextSnapshot.objects.get()
    assert Capture.objects.count() == 3 and snapshot.capture.url == abu_dhabi.DISTRICT_GEOJSON
    result = public_context("districts", query="منطقة")
    assert result["total"] == 1 and result["districts"][0]["district_id"] == 1


def test_school_archive_is_imported_without_inventing_a_network_clock():
    original = school_archive()
    result = execute_import(
        operation="public_context",
        scope="abu-dhabi:schools",
        actor="test-archive",
        execution_key="b" * 64,
        acquisition=lambda u, p: abu_dhabi.archive_response("abu-dhabi:schools", original),
    )
    assert result["status"] == "succeeded"
    snapshot = PublicContextSnapshot.objects.get()
    assert snapshot.capture.acquisition_method == "manual_archive_import"
    assert snapshot.capture.fetched_started_at is None
    assert public_context("schools")["timestamp_basis"] == "artifact_filesystem_time"
