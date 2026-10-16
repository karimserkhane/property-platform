import asyncio
import inspect
from types import SimpleNamespace

import httpx
from prefect.client.schemas.schedules import CronSchedule

from property_platform_ingestion.deployments import schedules_for
from property_platform_ingestion.registry import DATASETS


def test_initial_schedule_has_dubai_timezone_and_awaits_operator_activation():
    schedules = schedules_for(DATASETS[0], None)
    assert len(schedules) == 1
    assert schedules[0].active is False
    assert schedules[0].schedule.timezone == "Asia/Dubai"


def test_restart_preserves_ui_edited_cadence_and_active_state():
    edited = SimpleNamespace(
        schedule=CronSchedule(cron="0 8 * * 1", timezone="Asia/Dubai"),
        active=True,
        slug="operator",
        parameters={},
        max_scheduled_runs=None,
    )
    schedules = schedules_for(DATASETS[0], SimpleNamespace(schedules=[edited]))
    assert schedules[0].schedule.cron == "0 8 * * 1"
    assert schedules[0].active is True
    assert schedules[0].slug == "operator"


def test_deleted_schedule_is_not_recreated_on_restart():
    assert schedules_for(DATASETS[0], SimpleNamespace(schedules=[])) == []


def test_project_collectors_offer_weekend_cadences_and_preserve_operator_schedules():
    projects = [row for row in DATASETS if row.flow_name == "property-platform-project-details"]
    assert {row.name for row in projects} == {"project-details", "saadiyat-project-details"}
    assert {row.parameters.get("territory", "al-reem-island") for row in projects} == {
        "al-reem-island",
        "saadiyat-island",
    }
    for row in projects:
        assert row.cron.endswith("* * 6") and schedules_for(row, None)[0].active is False
        edited = SimpleNamespace(
            schedule=CronSchedule(cron="0 8 * * 1", timezone="Asia/Dubai"),
            active=True,
            slug="operator",
            parameters={},
            max_scheduled_runs=None,
        )
        preserved = schedules_for(row, SimpleNamespace(schedules=[edited]))
        assert len(preserved) == 1 and preserved[0].active is True
        assert preserved[0].schedule.cron == "0 8 * * 1"


def test_operator_media_intake_has_no_automatic_schedule():
    dataset = next(row for row in DATASETS if row.name == "project-media-files")
    assert dataset.cron is None and schedules_for(dataset, None) == []


def test_async_registration_awaits_the_factory_before_starting_runner(monkeypatch):
    from prefect.exceptions import ObjectNotFound

    from property_platform_ingestion import deployments

    received = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def read_deployment_by_name(self, name):
            request = httpx.Request("GET", "http://prefect.test/deployments/name")
            response = httpx.Response(404, request=request)
            raise ObjectNotFound(
                httpx.HTTPStatusError("Missing", request=request, response=response)
            )

    class Flow:
        async def ato_deployment(self, **kwargs):
            return SimpleNamespace(**kwargs)

    class Runner:
        def __init__(self, **kwargs):
            assert kwargs["limit"] == 1
            assert kwargs["pause_on_shutdown"] is False

        async def add_deployment(self, deployment):
            assert not inspect.isawaitable(deployment)
            received.append(deployment)

        async def start(self):
            received.append("started")

    monkeypatch.setattr(deployments, "invoke_domain", lambda request: {"status": "succeeded"})
    monkeypatch.setattr(deployments, "Runner", Runner)
    monkeypatch.setattr(deployments, "get_client", lambda: Client())
    monkeypatch.setattr(deployments, "DATASETS", DATASETS[:1])
    monkeypatch.setattr(deployments, "FLOWS", {DATASETS[0].flow_name: Flow()})
    asyncio.run(deployments.serve_datasets())
    assert received[0].name == "parcels-onwani"
    assert received[0].schedules[0].active is False
    assert received[-1] == "started"
