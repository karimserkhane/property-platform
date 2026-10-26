"""Operational retries commit with source writes, using real PostgreSQL/PostGIS."""

import copy
import hashlib
import os
from datetime import timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import psycopg
import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Orchestration integration requires real PostGIS", allow_module_level=True)

from test_onwani_postgis import feature, responses  # noqa: E402
from test_property_presentations_postgis import sample  # noqa: E402
from test_reem_evidence_postgis import imagery_receipt  # noqa: E402
from test_reem_map_postgis import district, osm  # noqa: E402
from test_reem_map_postgis import receipt as map_receipt

from property_platform.modules.catalog.models import Parcel  # noqa: E402
from property_platform.modules.evidence.maps import onwani, services  # noqa: E402
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    ImageryScene,
    IngestionExecution,
    IngestionRun,
    MapObservation,
    ParcelObservation,
    PropertyMedia,
    PropertyPresentation,
    Source,
)
from property_platform.modules.evidence.orchestration import (  # noqa: E402
    ImportBusy,
    execute_import,
    execution_result,
    record_acquisition_failure,
    reference_identity,
    reference_registry,
)

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]


def key(value):
    return hashlib.sha256(value.encode()).hexdigest()


def execute(operation="onwani", *, identity="first", scope="al-reem-island", **kwargs):
    return execute_import(
        operation=operation,
        scope=scope,
        execution_key=key(identity),
        actor="test-orchestrator",
        **kwargs,
    )


def test_committed_job_retry_and_preacquisition_lookup_are_noops():
    acquire = Mock(side_effect=responses([feature()]))
    first = execute(acquisition=acquire)
    second = execute(acquisition=acquire)
    assert first["status"] == second["status"] == "succeeded"
    assert second["reused"] and second["execution_id"] == first["execution_id"]
    assert acquire.call_count == 4
    assert Parcel.objects.count() == IngestionRun.objects.count() == 1
    assert IngestionExecution.objects.get().runs.count() == 1
    previous = execution_result(
        execution_key=key("first"),
        operation="onwani",
        scope="al-reem-island",
        actor="test-orchestrator",
    )
    assert previous["reused"] and previous["run_ids"] == first["run_ids"]


def test_failed_source_preserves_capture_and_same_job_can_retry():
    rejected = responses([feature()])[0]
    rejected[1]["http_status"] = 503
    failed = execute(acquisition=Mock(return_value=rejected))
    assert failed["status"] == "failed" and failed["error"] == "SourceError"
    assert Capture.objects.count() == IngestionRun.objects.count() == 1
    assert not Parcel.objects.exists()
    result = execute(acquisition=Mock(side_effect=responses([feature()])))
    assert result["status"] == "succeeded" and result["attempts"] == 2
    assert len(result["run_ids"]) == 2
    assert Parcel.objects.count() == 1


def test_transport_failure_has_operational_audit_without_a_fabricated_source():
    failed = record_acquisition_failure(
        operation="onwani",
        scope="al-reem-island",
        execution_key=key("first"),
        actor="test-orchestrator",
        error=TimeoutError("secret credentials"),
    )
    assert failed["status"] == "failed" and failed["error"] == "TimeoutError"
    assert failed["summary"] == {"phase": "acquisition"} and failed["run_ids"] == []
    assert not Source.objects.exists() and not Capture.objects.exists()
    result = execute(acquisition=Mock(side_effect=responses([feature()])))
    assert result["status"] == "succeeded" and result["attempts"] == 2


def test_failed_reconciliation_preserves_diagnostics_and_does_not_disable_retry():
    identity = {
        "operation": "onwani",
        "scope": "al-reem-island",
        "execution_key": key("first"),
        "actor": "test-orchestrator",
    }
    failed = record_acquisition_failure(**identity, error="TimeoutError")
    assert execution_result(**identity) is None
    recovered = execution_result(**identity, include_failed=True)
    assert recovered["reused"] and recovered["status"] == "failed"
    for field in ("execution_id", "error", "summary", "attempts", "started_at", "finished_at"):
        assert recovered[field] == failed[field]
    assert recovered["attempts"] == 1 and recovered["error"] == "TimeoutError"
    assert not Source.objects.exists() and not Capture.objects.exists()
    with pytest.raises(ValueError, match="another request"):
        execution_result(**{**identity, "actor": "another-operator"}, include_failed=True)
    result = execute(acquisition=Mock(side_effect=responses([feature()])))
    assert result["status"] == "succeeded" and result["attempts"] == 2
    assert result["execution_id"] == failed["execution_id"]
    assert execution_result(**identity)["status"] == "succeeded"
    assert IngestionExecution.objects.count() == Parcel.objects.count() == 1


@pytest.mark.parametrize(
    ("status", "payload"),
    [(406, b"Not acceptable"), (200, b'{"geometryType":"unexpected-source-schema"}')],
)
def test_precollection_rejection_preserves_complete_real_response_without_catalogue_write(
    status, payload
):
    now = timezone.now()
    receipt = {
        "url": onwani.BASE_URL + "?f=pjson",
        "http_status": status,
        "fetched_started_at": now - timedelta(milliseconds=10),
        "fetched_at": now,
        "etag": '"source-version"',
        "last_modified_raw": "",
        "acquisition_method": "scheduled_https_collect",
        "timestamp_basis": "collector_clock",
    }
    result = record_acquisition_failure(
        operation="onwani",
        scope="al-reem-island",
        execution_key=key("first"),
        actor="test-orchestrator",
        error="SourceError",
        received_acquisitions=[{"payload": payload, "receipt": receipt}],
    )
    assert result["status"] == "failed" and result["summary"]["capture_count"] == 1
    assert result["summary"]["http_statuses"] == [status]
    capture = Capture.objects.get()
    assert bytes(capture.payload) == payload and capture.http_status == status
    assert capture.content_sha256 == hashlib.sha256(payload).hexdigest()
    assert capture.fetched_at == now and capture.acquisition_method == "scheduled_https_collect"
    assert capture.run.status == "failed" and capture.run.source.key == onwani.SOURCE_KEY
    assert result["run_ids"] == [str(capture.run_id)]
    assert IngestionExecution.objects.get().runs.get().id == capture.run_id
    assert not Parcel.objects.exists() and not ParcelObservation.objects.exists()


@pytest.mark.parametrize("invalid", ["url", "chronology", "payload"])
def test_unqualified_failed_journal_is_rejected_before_operational_or_source_writes(invalid):
    now = timezone.now()
    receipt = {
        "url": onwani.BASE_URL + "?f=pjson",
        "http_status": 406,
        "fetched_started_at": now,
        "fetched_at": now,
        "etag": "",
        "last_modified_raw": "",
        "acquisition_method": "scheduled_https_collect",
        "timestamp_basis": "collector_clock",
    }
    payload = b"Actual response"
    if invalid == "url":
        receipt["url"] = "https://unregistered.example/source?f=pjson"
    elif invalid == "chronology":
        receipt["fetched_started_at"] = now + timedelta(days=1)
    else:
        payload = "Not actual bytes"
    with pytest.raises(ValueError):
        record_acquisition_failure(
            operation="onwani",
            scope="al-reem-island",
            execution_key=key("first"),
            actor="test-orchestrator",
            error="SourceError",
            received_acquisitions=[{"payload": payload, "receipt": receipt}],
        )
    assert not Source.objects.exists() and not IngestionExecution.objects.exists()


def test_property_retry_can_bind_first_receipt_after_transport_failure():
    _, profile, photo, receipts = sample()
    record_acquisition_failure(
        operation="property_presentations",
        scope="al-reem-island",
        execution_key=key("first"),
        actor="test-orchestrator",
        error="TimeoutError",
    )
    with patch(
        "property_platform.modules.evidence.projects.property_import.registry",
        return_value=([profile], {"example": photo}),
    ):
        result = execute("property_presentations", receipt=receipts)
    assert result["status"] == "succeeded" and result["attempts"] == 2
    assert IngestionExecution.objects.get().input_sha256 is not None


def test_unconsumed_staging_rolls_back_canonical_updates_before_completion():
    result = execute(
        acquisition=Mock(side_effect=responses([feature()])),
        completion_check=Mock(side_effect=ValueError("unconsumed response")),
    )
    assert result["status"] == "failed" and result["error"] == "ValueError"
    assert not Parcel.objects.exists() and not IngestionRun.objects.exists()


def test_quarantine_is_visible_and_is_not_blindly_retried():
    bad = feature()
    bad["geometry"]["rings"] = [[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]]
    acquire = Mock(side_effect=responses([bad, feature(2)]))
    first = execute(acquisition=acquire)
    assert first["status"] == "quarantined" and first["summary"]["quarantined"] == 1
    assert Parcel.objects.count() == 1
    assert execute(acquisition=acquire)["reused"]
    assert acquire.call_count == 4


def test_crash_before_completion_rolls_back_and_recovery_is_safe():
    IngestionExecution.objects.create(
        operation="onwani",
        scope="al-reem-island",
        execution_key=key("first"),
        actor="test-orchestrator",
    )
    with patch.object(IngestionExecution, "save", side_effect=SystemExit("simulated crash")):
        with pytest.raises(SystemExit):
            execute(acquisition=Mock(side_effect=responses([feature()])))
    assert not Parcel.objects.exists() and not IngestionRun.objects.exists()
    assert IngestionExecution.objects.get().status == "running"
    result = execute(acquisition=Mock(side_effect=responses([feature()])))
    assert result["status"] == "succeeded" and result["attempts"] == 3
    assert Parcel.objects.count() == IngestionRun.objects.count() == 1


def test_completion_failure_never_commits_catalogue_without_job_marker():
    IngestionExecution.objects.create(
        operation="onwani",
        scope="al-reem-island",
        execution_key=key("first"),
        actor="test-orchestrator",
    )
    original = IngestionExecution.save
    calls = 0

    def fail_once(obj, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("marker unavailable")
        return original(obj, *args, **kwargs)

    with patch.object(IngestionExecution, "save", fail_once):
        result = execute(acquisition=Mock(side_effect=responses([feature()])))
    assert result["status"] == "failed" and result["error"] == "ValueError"
    assert not Parcel.objects.exists() and not IngestionRun.objects.exists()
    assert result["run_ids"] == []


def test_one_reference_failure_is_reported_even_when_service_returns_normally():
    row = reference_registry()[0]
    identity = reference_identity(row["url"])
    result = execute(
        "references",
        scope=f"al-reem-island:{identity}",
        reference_key=identity,
        acquisition=Mock(side_effect=TimeoutError("secret URL should not reach diagnostics")),
    )
    assert result["status"] == "failed" and result["error"] == "TimeoutError"
    assert len(result["run_ids"]) == 1
    assert not Capture.objects.exists()
    assert "secret" not in result["error"]


def test_map_injected_acquisition_retains_source_owned_identity():
    import json

    district()
    acquire = Mock(return_value=(json.dumps(osm()).encode(), map_receipt()))
    result = execute("map", scope="al-reem-island:osm", acquisition=acquire)
    assert result["status"] == "succeeded" and result["summary"]["created"] == 3
    assert MapObservation.objects.count() == 3
    assert acquire.call_count == 1


def test_exact_property_receipt_replay_reuses_history_but_fresh_check_does_not():
    _, profile, photo, receipts = sample()
    with patch(
        "property_platform.modules.evidence.projects.property_import.registry",
        return_value=([profile], {"example": photo}),
    ):
        first = execute("property_presentations", receipt=receipts)
        replay = execute(
            "property_presentations", receipt=list(reversed(receipts)), identity="second"
        )
        assert first["status"] == "succeeded" and replay["reused"]
        assert replay["execution_id"] != first["execution_id"]
        assert replay["reused_from"] == first["execution_id"]
        assert PropertyPresentation.objects.count() == PropertyMedia.objects.count() == 1
        before = PropertyPresentation.objects.get().capture.fetched_at
        fresh = copy.deepcopy(receipts)
        now = timezone.now()
        for row in fresh:
            row["fetched_started_at"] = (now - timedelta(milliseconds=1)).isoformat()
            row["fetched_at"] = now.isoformat()
        result = execute("property_presentations", receipt=fresh, identity="third")
        assert result["status"] == "succeeded" and not result["reused"]
        assert PropertyPresentation.objects.count() == 2
        assert PropertyPresentation.objects.latest("id").capture.fetched_at > before


def test_historical_imagery_exact_replay_creates_no_extra_captures():
    rows = imagery_receipt()
    first = execute("imagery", receipt=rows)
    replay = execute("imagery", receipt=rows, identity="second")
    assert first["status"] == "succeeded" and replay["reused"]
    assert replay["execution_id"] != first["execution_id"]
    assert replay["execution_key"] == key("second")
    assert replay["reused_from"] == first["execution_id"]
    assert replay["run_ids"] == first["run_ids"]
    assert (
        ImageryScene.objects.count() == IngestionRun.objects.count() == Capture.objects.count() == 2
    )
    assert IngestionExecution.objects.count() == 2
    repeated = execute("imagery", receipt=rows, identity="second")
    assert repeated["execution_id"] == replay["execution_id"]
    assert repeated["reused_from"] == first["execution_id"]
    assert IngestionExecution.objects.count() == Capture.objects.count() == 2


def test_receipt_replay_audits_new_operator_and_run_without_rewriting_acquisition():
    rows = imagery_receipt()
    first = execute("imagery", receipt=rows)
    before = list(Capture.objects.order_by("id").values("id", "fetched_at", "run__actor"))
    run_id = uuid4()
    replay = execute_import(
        operation="imagery",
        scope="al-reem-island",
        execution_key=key("new-prefect-run"),
        actor="another-operator",
        prefect_flow_run_id=run_id,
        receipt=rows,
    )
    wrapper = IngestionExecution.objects.get(pk=replay["execution_id"])
    assert wrapper.actor == "another-operator" and wrapper.prefect_flow_run_id == run_id
    assert str(wrapper.reused_from_id) == first["execution_id"]
    assert wrapper.input_sha256 is None and wrapper.finished_at >= wrapper.started_at
    assert wrapper.runs.count() == 2
    assert list(Capture.objects.order_by("id").values("id", "fetched_at", "run__actor")) == before


def test_failed_bound_receipt_cannot_be_rebound_to_another_jobs_successful_receipt():
    original = imagery_receipt()
    failed = execute(
        "imagery",
        receipt=original,
        completion_check=Mock(side_effect=ValueError("completion interrupted")),
    )
    assert failed["status"] == "failed"
    different = copy.deepcopy(original)
    for row in different:
        row["fetched_started_at"] = timezone.now().isoformat()
        row["fetched_at"] = timezone.now().isoformat()
    other = execute("imagery", receipt=different, identity="other-job")
    assert other["status"] == "succeeded"
    with pytest.raises(ValueError, match="differs from its original"):
        execute("imagery", receipt=different)
    execution = IngestionExecution.objects.get(pk=failed["execution_id"])
    assert execution.status == "failed" and execution.attempts == 1
    assert execution.input_sha256 is not None and execution.reused_from_id is None
    assert IngestionExecution.objects.count() == Capture.objects.count() == 2


def test_busy_source_does_not_consume_job_identity_or_write_evidence():
    with psycopg.connect(**connection.get_connection_params()) as other:
        other.execute("SELECT pg_advisory_lock(%s)", [services.LOCK_KEY])
        with pytest.raises(ImportBusy):
            execute()
    assert not IngestionExecution.objects.exists() and not Source.objects.exists()


@pytest.mark.parametrize(
    ("operation", "scope"),
    [
        ("shell", "al-reem-island"),
        ("onwani", "dubai"),
        ("map", "al-reem-island:any"),
        ("references", "al-reem-island:" + "0" * 40),
    ],
)
def test_unknown_operations_territories_and_sources_are_inert(operation, scope):
    with pytest.raises(ValueError):
        execute(operation, scope=scope)
    assert not IngestionExecution.objects.exists() and not Source.objects.exists()


def test_execution_identity_cannot_be_rebound_to_another_scope():
    execute(acquisition=Mock(side_effect=responses([feature()])))
    with pytest.raises(ValueError, match="another request"):
        execute("map", scope="al-reem-island:street")
    assert IngestionExecution.objects.count() == 1


def test_execution_tables_are_in_evidence_and_database_rejects_invalid_lifecycle():
    with connection.cursor() as cursor:
        for name in ("ingestion_execution", "ingestion_execution_run"):
            cursor.execute(
                "SELECT to_regclass(%s), to_regclass(%s)", ["evidence." + name, "public." + name]
            )
            expected, public = cursor.fetchone()
            assert expected is not None and public is None
    with pytest.raises(IntegrityError), transaction.atomic():
        IngestionExecution.objects.create(
            operation="onwani",
            scope="al-reem-island",
            execution_key=key("first"),
            actor="test",
            status="succeeded",
            finished_at=None,
        )
