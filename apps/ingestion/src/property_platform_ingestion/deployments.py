"""Register packaged flows while preserving schedules edited in the Prefect UI."""

import asyncio
from collections import defaultdict
from datetime import UTC, datetime

from prefect.client.orchestration import get_client
from prefect.client.schemas.actions import DeploymentScheduleCreate
from prefect.client.schemas.filters import (
    FlowRunFilter,
    FlowRunFilterDeploymentId,
    FlowRunFilterNextScheduledStartTime,
    FlowRunFilterState,
    FlowRunFilterStateType,
)
from prefect.client.schemas.objects import StateType
from prefect.client.schemas.responses import SetStateStatus
from prefect.client.schemas.schedules import CronSchedule
from prefect.exceptions import ObjectNotFound
from prefect.flows import EntrypointType
from prefect.logging import get_logger
from prefect.runner import Runner
from prefect.states import Cancelled, Crashed

from . import __version__
from .flows import FLOWS
from .registry import DATASETS, TERRITORY, TIMEZONE
from .runtime import invoke_domain

logger = get_logger("property_platform_ingestion.runner")
PAGE = 200
# Queues are read every minute: work waits at most about as long as with the former
# two-minute drains (A44).
DRAIN_CHECK_SECONDS = 60
PENDING_TIMEOUT = 50
IN_FLIGHT = frozenset(
    {StateType.SCHEDULED, StateType.PENDING, StateType.RUNNING, StateType.CANCELLING}
)


def _cadence(dataset, item):
    # An initial schedule left on a retired default follows the reviewed cadence, or goes
    # when the dataset no longer has one (queue drains, A44); an operator edit (another cron
    # or slug) is kept, and so is the active flag.
    if item.slug == "initial-cadence" and getattr(item.schedule, "cron", None) in (
        dataset.retired_crons
    ):
        if dataset.cron is None:
            return None
        return CronSchedule(cron=dataset.cron, timezone=item.schedule.timezone)
    return item.schedule


def schedules_for(dataset, existing):
    if existing is not None:
        # An empty list also matters: removing a schedule in the UI stays removed.
        return [
            DeploymentScheduleCreate(
                schedule=schedule,
                active=item.active,
                slug=item.slug,
                parameters=item.parameters,
                max_scheduled_runs=item.max_scheduled_runs,
            )
            for item in existing.schedules
            if (schedule := _cadence(dataset, item)) is not None
        ]
    if dataset.cron is None:
        return []
    return [
        DeploymentScheduleCreate(
            schedule=CronSchedule(cron=dataset.cron, timezone=TIMEZONE),
            active=False,
            slug="initial-cadence",
        )
    ]


async def _flow_runs(client, flow_run_filter):
    runs = []
    while page := await client.read_flow_runs(
        flow_run_filter=flow_run_filter, limit=PAGE, offset=len(runs)
    ):
        runs += page
    return runs


async def crash_orphaned_runs(client, deployment_ids, before):
    """Close runs a previous runner process left pending or running.

    This runner alone executes these deployments, so a run it did not start cannot still be
    executing. Left open, such a run keeps its deployment's only concurrency slot: every
    later walking-areas run waited behind one from 27/10/2026 until A26.
    """
    runs = await _flow_runs(
        client,
        FlowRunFilter(
            deployment_id=FlowRunFilterDeploymentId(any_=list(deployment_ids)),
            state=FlowRunFilterState(
                type=FlowRunFilterStateType(
                    any_=[StateType.PENDING, StateType.RUNNING, StateType.CANCELLING]
                )
            ),
        ),
    )
    orphans = [run for run in runs if run.state and run.state.timestamp < before]
    for run in orphans:
        # Forced: the orchestration rules would wait for a process that no longer exists;
        # leaving the state still releases the deployment slot.
        await client.set_flow_run_state(
            run.id, Crashed(message="Left open by a previous runner process."), force=True
        )
    return len(orphans)


async def cancel_superseded_drains(client, deployment_ids, now=None):
    """Keep the latest overdue scheduled run of each queue drain and cancel the others.

    With one runner slot, overdue runs are taken oldest first: after a long job or a stopped
    runner, minute drains queued thousands of runs ahead of every manual launch. One run
    empties the queue, so the earlier ones add nothing. Manual runs are never cancelled.
    """
    now = now or datetime.now(UTC)
    runs = await _flow_runs(
        client,
        FlowRunFilter(
            deployment_id=FlowRunFilterDeploymentId(any_=list(deployment_ids)),
            state=FlowRunFilterState(type=FlowRunFilterStateType(any_=[StateType.SCHEDULED])),
            next_scheduled_start_time=FlowRunFilterNextScheduledStartTime(before_=now),
        ),
    )
    overdue = defaultdict(list)
    for run in runs:
        if run.auto_scheduled:
            overdue[run.deployment_id].append(run)
    cancelled = 0
    for queued in overdue.values():
        queued.sort(key=lambda run: run.next_scheduled_start_time)
        for run in queued[:-1]:
            # Not forced: a run the runner has just submitted is refused or cancelled before
            # it starts, and a later run of the same drain is already due.
            result = await client.set_flow_run_state(
                run.id, Cancelled(message="Superseded by a later run of the same queue.")
            )
            cancelled += result.status == SetStateStatus.ACCEPT
    return cancelled


async def dispatch_drains(client, drains, pending):
    """Start one run of each drain whose queue holds work and that has none in flight.

    A drain used to run every two minutes, empty or not: 2,880 runs a day, each with its
    execution row and logs, and none for walking areas that had no graph (A44). The queue is
    now read first, in a domain subprocess that writes nothing, so an empty queue leaves no
    trace in Prefect. A paused deployment is left alone, as its schedule would be.
    """
    in_flight = await _flow_runs(
        client,
        FlowRunFilter(
            deployment_id=FlowRunFilterDeploymentId(any_=list(drains.values())),
            state=FlowRunFilterState(type=FlowRunFilterStateType(any_=list(IN_FLIGHT))),
        ),
    )
    busy = {run.deployment_id for run in in_flight}
    started = []
    for name, deployment_id in drains.items():
        if not pending.get(name) or deployment_id in busy:
            continue
        if (await client.read_deployment(deployment_id)).paused:
            continue
        await client.create_flow_run_from_deployment(deployment_id, tags=["queue-work"])
        started.append(name)
    return started


def pending_work():
    result = invoke_domain({"operation": "pending_work"}, timeout=PENDING_TIMEOUT)
    return {name: int(count) for name, count in result["summary"].items()}


async def keep_drains_current(drains):
    while True:
        try:
            # The domain subprocess blocks; it runs off the runner's event loop.
            pending = await asyncio.to_thread(pending_work)
            async with get_client() as client:
                cancelled = await cancel_superseded_drains(client, list(drains.values()))
                started = await dispatch_drains(client, drains, pending)
            if cancelled:
                logger.info("Cancelled %d superseded queue drain runs", cancelled)
            if started:
                logger.info("Started queue drains with pending work: %s", ", ".join(started))
        except Exception:
            # A failed pass leaves the work for the next one; the runner keeps serving.
            logger.exception("Queue drain check failed")
        await asyncio.sleep(DRAIN_CHECK_SECONDS)


async def serve_datasets():
    started = datetime.now(UTC)
    invoke_domain({"operation": "check"})
    runner = Runner(
        name="property-platform-ingestion", limit=1, pause_on_shutdown=False, webserver=True
    )
    deployment_ids, drains = [], {}
    async with get_client() as client:
        for dataset in DATASETS:
            try:
                existing = await client.read_deployment_by_name(
                    f"{dataset.flow_name}/{dataset.name}",
                )
            except ObjectNotFound:
                existing = None
            parameters = dict(dataset.parameters)
            if existing is not None:
                parameters.update(existing.parameters)
            deployment = await FLOWS[dataset.flow_name].ato_deployment(
                name=dataset.name,
                description=dataset.description,
                schedules=schedules_for(dataset, existing),
                paused=existing.paused if existing else False,
                concurrency_limit=1,
                parameters=parameters,
                tags=["ingestion", dataset.parameters.get("territory", TERRITORY)],
                version=__version__,
                entrypoint_type=EntrypointType.MODULE_PATH,
            )
            deployment_id = await runner.add_deployment(deployment)
            deployment_ids.append(deployment_id)
            if dataset.drain:
                drains[dataset.name] = deployment_id
        crashed = await crash_orphaned_runs(client, deployment_ids, started)
        if crashed:
            logger.info("Crashed %d runs left open by a previous runner process", crashed)
    watcher = asyncio.create_task(keep_drains_current(drains)) if drains else None
    try:
        await runner.start()
    finally:
        if watcher:
            watcher.cancel()


def serve():
    asyncio.run(serve_datasets())
