from datetime import UTC, datetime, timedelta
from fnmatch import fnmatch
from types import SimpleNamespace
from uuid import uuid4

from prefect.client.schemas.objects import StateType
from property_platform.modules.evidence.source_families import FAMILIES

from property_platform_ingestion import operations
from property_platform_ingestion.operations import (
    REPEATED_FAILURES,
    operations_report,
)
from property_platform_ingestion.registry import DATASETS

NOW = datetime(2026, 11, 9, 6, 15, tzinfo=UTC)


def deployment(name, paused=False):
    return SimpleNamespace(id=uuid4(), name=name, paused=paused)


def finished(state):
    return SimpleNamespace(
        state_type=state,
        state=SimpleNamespace(timestamp=NOW - timedelta(hours=1)),
    )


def waiting(item, delay):
    return SimpleNamespace(deployment_id=item.id, next_scheduled_start_time=NOW - delay)


class Client:
    def __init__(self, deployments, runs=None, scheduled=()):
        self.deployments = deployments
        self.runs = runs or {}
        self.scheduled = list(scheduled)

    def read_deployments(self, limit, offset):
        return self.deployments[offset : offset + limit]

    def read_flow_runs(self, flow_run_filter, sort, limit):
        if flow_run_filter.state.type.any_ == [StateType.SCHEDULED]:
            assert flow_run_filter.next_scheduled_start_time.before_ == NOW - operations.LATE_AFTER
            return self.scheduled
        assert limit == REPEATED_FAILURES
        return self.runs.get(flow_run_filter.deployment_id.any_[0], [])


def test_only_repeated_failures_of_active_deployments_are_reported():
    broken = deployment("saadiyat-project-details")
    recovered = deployment("map-osm")
    young = deployment("map-street")
    paused = deployment("restore-check", paused=True)
    failed = [finished(StateType.FAILED), finished(StateType.CRASHED), finished(StateType.FAILED)]
    client = Client(
        [broken, recovered, young, paused],
        {
            broken.id: failed,
            recovered.id: [finished(StateType.COMPLETED), *failed[:2]],
            young.id: failed[:2],
            paused.id: failed,
        },
    )
    report, totals = operations_report(client, NOW)
    assert [item["deployment"] for item in report["failing_deployments"]] == [
        "saadiyat-project-details"
    ]
    assert report["failing_deployments"][0]["failures"] == REPEATED_FAILURES
    assert totals == {"failing_deployments": 1, "late_queues": 0}


def test_late_queues_are_grouped_oldest_first_and_unknown_runs_ignored():
    drain = deployment("walking-areas")
    weekly = deployment("map-osm")
    client = Client(
        [drain, weekly],
        scheduled=[
            waiting(weekly, timedelta(hours=9)),
            waiting(drain, timedelta(hours=2)),
            waiting(drain, timedelta(hours=1)),
            waiting(deployment("removed"), timedelta(hours=20)),
        ],
    )
    report, _ = operations_report(client, NOW)
    assert [(item["deployment"], item["runs"]) for item in report["late_queues"]] == [
        ("map-osm", 1),
        ("walking-areas", 2),
    ]
    assert report["late_queues"][1]["oldest_expected_at"] == (NOW - timedelta(hours=2)).isoformat()


def test_findings_are_bounded_for_the_domain_request_but_totals_are_not():
    names = [deployment(f"deployment-{index}") for index in range(40)]
    failed = [finished(StateType.FAILED)] * REPEATED_FAILURES
    report, totals = operations_report(Client(names, {item.id: failed for item in names}), NOW)
    assert len(report["failing_deployments"]) == operations.MAX_ITEMS
    assert totals["failing_deployments"] == 40


def test_each_family_names_deployments_that_exist():
    names = [dataset.name for dataset in DATASETS]
    for family in FAMILIES:
        for pattern in family.deployments:
            assert any(fnmatch(name, pattern) for name in names), (family.key, pattern)


def test_new_report_deployment_starts_inactive():
    from property_platform_ingestion.deployments import schedules_for

    dataset = next(item for item in DATASETS if item.name == "source-freshness")
    assert [schedule.active for schedule in schedules_for(dataset, None)] == [False]
