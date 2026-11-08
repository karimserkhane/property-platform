"""What the daily freshness report reads from Prefect: repeated failures and late queues."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from prefect.client.schemas.filters import (
    FlowRunFilter,
    FlowRunFilterDeploymentId,
    FlowRunFilterNextScheduledStartTime,
    FlowRunFilterState,
    FlowRunFilterStateType,
)
from prefect.client.schemas.objects import StateType
from prefect.client.schemas.sorting import FlowRunSort

REPEATED_FAILURES = 3
# A queue is late past this delay: the two-minute drains are often a minute or two behind.
LATE_AFTER = timedelta(minutes=30)
PAGE = 200
# Keeps the report inside the domain request budget; more than this is already an outage.
MAX_ITEMS = 25
FAILED = frozenset({StateType.FAILED, StateType.CRASHED})


def _deployments(client):
    deployments, page = [], True
    while page:
        page = client.read_deployments(limit=PAGE, offset=len(deployments))
        deployments += page
    return deployments


def failing_deployments(client, deployments):
    """Active deployments whose last finished runs all failed; a cancelled run is not one."""
    failing = []
    for deployment in deployments:
        if deployment.paused:
            continue
        runs = client.read_flow_runs(
            flow_run_filter=FlowRunFilter(
                deployment_id=FlowRunFilterDeploymentId(any_=[deployment.id]),
                state=FlowRunFilterState(
                    type=FlowRunFilterStateType(any_=[StateType.COMPLETED, *FAILED])
                ),
            ),
            sort=FlowRunSort.EXPECTED_START_TIME_DESC,
            limit=REPEATED_FAILURES,
        )
        if len(runs) == REPEATED_FAILURES and all(run.state_type in FAILED for run in runs):
            failing.append(
                {
                    "deployment": deployment.name,
                    "failures": REPEATED_FAILURES,
                    "last_failed_at": runs[0].state.timestamp.isoformat(),
                }
            )
    return sorted(failing, key=lambda item: item["deployment"])


def late_queues(client, deployments, now):
    """Deployments with scheduled runs still waiting past the delay, oldest wait first."""
    names = {deployment.id: deployment.name for deployment in deployments}
    runs = client.read_flow_runs(
        flow_run_filter=FlowRunFilter(
            state=FlowRunFilterState(type=FlowRunFilterStateType(any_=[StateType.SCHEDULED])),
            next_scheduled_start_time=FlowRunFilterNextScheduledStartTime(before_=now - LATE_AFTER),
        ),
        sort=FlowRunSort.EXPECTED_START_TIME_ASC,
        limit=PAGE,
    )
    waiting = defaultdict(list)
    for run in runs:
        if run.deployment_id in names:
            waiting[names[run.deployment_id]].append(run.next_scheduled_start_time)
    late = [
        {
            "deployment": name,
            "runs": len(times),
            "oldest_expected_at": min(times).isoformat(),
        }
        for name, times in waiting.items()
    ]
    return sorted(late, key=lambda item: item["oldest_expected_at"])


def operations_report(client, now=None):
    now = now or datetime.now(UTC)
    deployments = _deployments(client)
    failing = failing_deployments(client, deployments)
    late = late_queues(client, deployments, now)
    return (
        {"failing_deployments": failing[:MAX_ITEMS], "late_queues": late[:MAX_ITEMS]},
        {"failing_deployments": len(failing), "late_queues": len(late)},
    )
