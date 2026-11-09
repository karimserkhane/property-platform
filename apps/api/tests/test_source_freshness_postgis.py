"""A lost source becomes late and keeps its facts: tested on real typed observations."""

import os
from datetime import timedelta

import pytest

if os.environ.get("PROPERTY_PLATFORM_TEST_POSTGIS") != "1":
    pytest.skip("Requires PostgreSQL/PostGIS", allow_module_level=True)

from django.test import override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402
from django.utils.dateparse import parse_datetime  # noqa: E402
from test_public_context_postgis import execute  # noqa: E402
from test_public_context_protocol import facility  # noqa: E402

from property_platform.api import read_cache  # noqa: E402
from property_platform.modules.evidence.history.source_freshness import (  # noqa: E402
    family_freshness,
    latest_report,
    record_report,
    state_at,
)
from property_platform.modules.evidence.models import (  # noqa: E402
    Capture,
    HealthFacilityObservation,
    IngestionRun,
    Source,
)
from property_platform.modules.publication.context_preview import public_context  # noqa: E402

pytestmark = [pytest.mark.postgis, pytest.mark.django_db(transaction=True)]

NOTHING = {"failing_deployments": [], "late_queues": []}


def row(family):
    return next(item for item in family_freshness() if item["family"] == family)


def add_run(key, status, finished_at):
    source, _ = Source.objects.get_or_create(
        key=key, defaults={"name": key, "url": "https://example.com/" + key}
    )
    run = IngestionRun.objects.create(source=source, actor="test", connector_version="v1")
    IngestionRun.objects.filter(pk=run.pk).update(
        started_at=finished_at - timedelta(minutes=1), finished_at=finished_at, status=status
    )
    return run


def test_a_lost_source_turns_late_and_keeps_every_documented_fact():
    assert execute([facility()])["status"] == "succeeded"
    before = row("public-context")
    published = public_context("health")
    assert before["last_success_at"] is not None and published["total"] == 1

    failed_at = before["last_success_at"] + timedelta(days=40)
    source = IngestionRun.objects.get().source
    IngestionRun.objects.create(
        source=source,
        actor="test",
        connector_version="v2",
        status="failed",
        error="SourceUnavailable",
        finished_at=failed_at,
    )

    after = row("public-context")
    assert after["last_success_at"] == before["last_success_at"]
    assert after["late_from"] == before["last_success_at"] + timedelta(days=9)
    assert state_at(after, failed_at) == "review"
    assert HealthFacilityObservation.objects.count() == 1
    assert public_context("health") == published


def test_states_follow_the_family_thresholds_and_quarantine_counts_as_success():
    success = timezone.now() - timedelta(days=10)
    add_run("adrec:market-data:indices", "quarantined", success)
    current = row("adrec-market")
    assert current["last_success_at"] == success
    assert state_at(current, success + timedelta(days=8)) == "current"
    assert state_at(current, success + timedelta(days=9)) == "late"
    assert state_at(current, success + timedelta(days=30)) == "review"
    empty = row("overture")
    assert empty["last_success_at"] is None and empty["sources_total"] == 0
    assert state_at(empty, timezone.now()) == "never"


def test_partial_failures_are_counted_and_the_longest_prefix_decides_the_family():
    now = timezone.now()
    add_run("project:fresh", "succeeded", now)
    add_run("project:forgotten", "succeeded", now - timedelta(days=20))
    add_run("project-acquisition:saadiyat-island:never", "failed", now)
    pages = row("developer-pages")
    assert (pages["sources_total"], pages["sources_behind"]) == (3, 2)

    add_run("project-discovery:saadiyat-island:adrec-saadiyat-register", "succeeded", now)
    assert row("adrec-register")["sources_total"] == 1
    assert row("developer-pages")["sources_total"] == 3
    add_run("dmt:onwani:smarthub:plot:adm:reem", "succeeded", now)
    add_run("dmt:onwani:reem:street", "succeeded", now)
    assert row("parcels-onwani")["sources_total"] == 1
    assert row("public-context")["sources_total"] == 1


def test_report_is_captured_once_per_prefect_run_and_read_back():
    add_run("osm:reem:osm", "succeeded", timezone.now() - timedelta(days=12))
    failing = [
        {"deployment": "map-osm", "failures": 3, "last_failed_at": "2026-11-08T04:45:00+00:00"}
    ]
    assert latest_report() is None

    first = record_report(
        actor="Prefect/run/scheduled",
        run_key="source-freshness:run",
        operations={"failing_deployments": failing, "late_queues": []},
    )
    again = record_report(
        actor="Prefect/run/scheduled", run_key="source-freshness:run", operations=NOTHING
    )

    assert first == again
    assert Capture.objects.filter(run__source__key="source-freshness-report").count() == 1
    assert next(f for f in first["summary"]["families"] if f["family"] == "osm")["state"] == "late"
    report = latest_report()
    assert report["failing_deployments"] == failing and report["late_queues"] == []


@pytest.mark.parametrize(
    "operations",
    [
        {"failing_deployments": [{"deployment": "x"}], "late_queues": []},
        {"failing_deployments": "x", "late_queues": []},
    ],
)
def test_report_refuses_malformed_findings(operations):
    with pytest.raises(ValueError):
        record_report(actor="a", run_key="k", operations=operations)
    assert not IngestionRun.objects.exists()


def test_the_read_is_cached_and_a_new_success_refreshes_it(client):
    read_cache.store.clear()
    add_run("overture:reem:places", "succeeded", timezone.now() - timedelta(days=1))
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        first = client.get("/api/v1/preview/source-freshness")
        assert first.status_code == 200
        unchanged = client.get(
            "/api/v1/preview/source-freshness", headers={"If-None-Match": first["ETag"]}
        )
        assert unchanged.status_code == 304
        latest = timezone.now()
        add_run("overture:reem:places", "succeeded", latest)
        fresh = client.get("/api/v1/preview/source-freshness")
    assert fresh.status_code == 200
    overture = next(item for item in fresh.json()["families"] if item["family"] == "overture")
    assert abs(parse_datetime(overture["last_success_at"]) - latest) < timedelta(milliseconds=1)
    assert fresh.json()["operations"] is None
