"""Register packaged flows while preserving schedules edited in the Prefect UI."""

import asyncio

from prefect.client.orchestration import get_client
from prefect.client.schemas.actions import DeploymentScheduleCreate
from prefect.client.schemas.schedules import CronSchedule
from prefect.exceptions import ObjectNotFound
from prefect.flows import EntrypointType
from prefect.runner import Runner

from . import __version__
from .flows import FLOWS
from .registry import DATASETS, TERRITORY, TIMEZONE
from .runtime import invoke_domain


def schedules_for(dataset, existing):
    if existing is not None:
        # An empty list also matters: removing a schedule in the UI stays removed.
        return [
            DeploymentScheduleCreate(
                schedule=item.schedule,
                active=item.active,
                slug=item.slug,
                parameters=item.parameters,
                max_scheduled_runs=item.max_scheduled_runs,
            )
            for item in existing.schedules
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


async def serve_datasets():
    invoke_domain({"operation": "check"})
    runner = Runner(
        name="property-platform-ingestion", limit=1, pause_on_shutdown=False, webserver=True
    )
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
            await runner.add_deployment(deployment)
    await runner.start()


def serve():
    asyncio.run(serve_datasets())
