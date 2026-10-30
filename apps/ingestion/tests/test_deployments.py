import asyncio
import inspect
from collections import defaultdict
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import httpx
from prefect.client.schemas.objects import StateType
from prefect.client.schemas.responses import SetStateStatus
from prefect.client.schemas.schedules import CronSchedule

from property_platform_ingestion.deployments import schedules_for
from property_platform_ingestion.registry import DATASETS, TERRITORIES


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
    assert {row.name for row in projects} == {
        "project-details",
        "saadiyat-project-details",
        "maryah-project-details",
    }
    assert {row.parameters.get("territory", "al-reem-island") for row in projects} == set(
        TERRITORIES
    )
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


def test_maryah_has_independent_audited_sources_and_inactive_initial_schedules():
    maryah = {
        row.name: row for row in DATASETS if row.parameters.get("territory") == "al-maryah-island"
    }
    assert set(maryah) == {
        "maryah-parcels-adsdi",
        "maryah-parcels-onwani",
        "maryah-map-district",
        "maryah-map-community",
        "maryah-map-street",
        "maryah-map-osm",
        "maryah-osm-bootstrap",
        "maryah-places-overture",
        "maryah-project-references",
        "maryah-project-details",
        "maryah-project-discovery",
        "adrec-maryah-sales",
    }
    for dataset in maryah.values():
        assert all(schedule.active is False for schedule in schedules_for(dataset, None))
    assert schedules_for(maryah["maryah-osm-bootstrap"], None) == []


def test_prefect_parameters_accept_maryah_on_every_island_collector():
    from property_platform_ingestion.flows import FLOWS

    for name in (
        "property-platform-sdi-parcels",
        "property-platform-parcels",
        "property-platform-map",
        "property-platform-references",
        "property-platform-presentations",
        "property-platform-project-details",
        "property-platform-project-discovery",
        "property-platform-osm-bootstrap",
    ):
        parameter = FLOWS[name].parameters.model_dump()["properties"]["territory"]
        assert set(parameter["enum"]) == set(TERRITORIES)


def test_local_scene_receipts_do_not_advertise_unregistered_island_coverage():
    from property_platform_ingestion.flows import imagery

    parameter = imagery.parameters.model_dump()["properties"]["territory"]
    assert parameter["const"] == "al-reem-island"


def test_async_registration_awaits_the_factory_before_starting_runner(monkeypatch):
    from prefect.exceptions import ObjectNotFound

    from property_platform_ingestion import deployments

    received = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def read_flow_runs(self, **kwargs):
            received.append("orphans checked")
            return []

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
            return uuid4()

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
    # Runs left open by a previous runner are closed before this one takes any run.
    assert received[1:] == ["orphans checked", "started"]


def run(deployment_id, minute, *, state=StateType.SCHEDULED, auto=True):
    at = datetime(2026, 10, 30, 4, minute, tzinfo=UTC)
    return SimpleNamespace(
        id=uuid4(),
        deployment_id=deployment_id,
        auto_scheduled=auto,
        next_scheduled_start_time=at,
        state=SimpleNamespace(type=state, timestamp=at),
    )


class Runs:
    """Prefect client double: pages `runs` and records proposed states."""

    def __init__(self, runs, status=SetStateStatus.ACCEPT):
        self.runs, self.status, self.proposed, self.filters = runs, status, [], []

    async def read_flow_runs(self, *, flow_run_filter, limit, offset):
        self.filters.append(flow_run_filter)
        return self.runs[offset : offset + limit]

    async def set_flow_run_state(self, flow_run_id, state, force=False):
        self.proposed.append((flow_run_id, state.type, force))
        return SimpleNamespace(status=self.status)


def test_queue_drains_run_every_two_minutes_and_follow_from_the_retired_minute_cadence():
    drains = {row.name: row for row in DATASETS if row.drain}
    assert set(drains) == {
        "walking-areas",
        "basemap-openfreemap",
        "basemap-sentinel-worldcover-2020",
        "basemap-sentinel-worldcover-2021",
    }
    assert drains["walking-areas"].cron == "1-59/2 * * * *"
    assert drains["basemap-openfreemap"].cron == "*/2 * * * *"
    activated = SimpleNamespace(
        schedule=CronSchedule(cron="* * * * *", timezone="Asia/Dubai"),
        active=True,
        slug="initial-cadence",
        parameters={},
        max_scheduled_runs=None,
    )
    moved = schedules_for(drains["walking-areas"], SimpleNamespace(schedules=[activated]))
    assert moved[0].schedule.cron == "1-59/2 * * * *"
    assert moved[0].schedule.timezone == "Asia/Dubai"
    assert moved[0].active is True and moved[0].slug == "initial-cadence"
    # An operator's own minute schedule is theirs to change.
    edited = SimpleNamespace(**{**vars(activated), "slug": "operator"})
    kept = schedules_for(drains["walking-areas"], SimpleNamespace(schedules=[edited]))
    assert kept[0].schedule.cron == "* * * * *"


def test_runs_left_open_by_a_previous_runner_are_crashed_and_new_ones_kept():
    from property_platform_ingestion.deployments import crash_orphaned_runs

    deployment = uuid4()
    stale = run(deployment, 0, state=StateType.RUNNING)
    submitting = run(deployment, 1, state=StateType.PENDING)
    current = run(deployment, 30, state=StateType.RUNNING)
    client = Runs([stale, submitting, current])
    started = datetime(2026, 10, 30, 4, 10, tzinfo=UTC)
    assert asyncio.run(crash_orphaned_runs(client, [deployment], started)) == 2
    assert client.proposed == [
        (stale.id, StateType.CRASHED, True),
        (submitting.id, StateType.CRASHED, True),
    ]
    states = client.filters[0].state.type.any_
    assert set(states) == {StateType.PENDING, StateType.RUNNING, StateType.CANCELLING}


def test_only_the_latest_overdue_run_of_each_queue_drain_is_kept(monkeypatch):
    from property_platform_ingestion import deployments

    monkeypatch.setattr(deployments, "PAGE", 2)
    walking, basemap = uuid4(), uuid4()
    walking_runs = [run(walking, minute) for minute in (3, 1, 2)]
    manual = run(walking, 0, auto=False)
    basemap_runs = [run(basemap, 1)]
    client = Runs([*walking_runs, manual, *basemap_runs])
    now = datetime(2026, 10, 30, 4, 5, tzinfo=UTC)
    cancelled = asyncio.run(deployments.cancel_superseded_drains(client, [walking, basemap], now))
    assert cancelled == 2
    assert client.proposed == [
        (walking_runs[1].id, StateType.CANCELLED, False),
        (walking_runs[2].id, StateType.CANCELLED, False),
    ]
    assert client.filters[0].next_scheduled_start_time.before_ == now
    # A run the runner took meanwhile refuses the cancellation and is not counted.
    refused = Runs([run(walking, 1), run(walking, 2)], status=SetStateStatus.REJECT)
    assert asyncio.run(deployments.cancel_superseded_drains(refused, [walking], now)) == 0


def test_runner_checks_superseded_drains_while_it_serves(monkeypatch):
    from property_platform_ingestion import deployments

    checked, ids = [], {}

    async def keep_drains_current(deployment_ids):
        checked.append(deployment_ids)
        await asyncio.Event().wait()

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def read_deployment_by_name(self, name):
            return SimpleNamespace(schedules=[], parameters={}, paused=False)

        async def read_flow_runs(self, **kwargs):
            return []

    class Flow:
        async def ato_deployment(self, **kwargs):
            return SimpleNamespace(**kwargs)

    class Runner:
        def __init__(self, **kwargs):
            pass

        async def add_deployment(self, deployment):
            return ids.setdefault(deployment.name, uuid4())

        async def start(self):
            await asyncio.sleep(0)

    drains = [row for row in DATASETS if row.drain]
    monkeypatch.setattr(deployments, "invoke_domain", lambda request: {"status": "succeeded"})
    monkeypatch.setattr(deployments, "Runner", Runner)
    monkeypatch.setattr(deployments, "get_client", lambda: Client())
    monkeypatch.setattr(deployments, "keep_drains_current", keep_drains_current)
    monkeypatch.setattr(deployments, "DATASETS", (DATASETS[0], *drains))
    monkeypatch.setattr(deployments, "FLOWS", defaultdict(Flow))
    asyncio.run(deployments.serve_datasets())
    assert checked == [[ids[row.name] for row in drains]]


def test_emirate_district_imports_are_manual_per_municipality():
    from property_platform_ingestion.flows import FLOWS

    rows = [r for r in DATASETS if r.flow_name == "property-platform-sdi-district-parcels"]
    assert {r.parameters["municipality"] for r in rows} == {"ADM", "AAM", "WRM"}
    assert all(r.cron is None and schedules_for(r, None) == [] for r in rows)
    flow = FLOWS["property-platform-sdi-district-parcels"]
    parameter = flow.parameters.model_dump()["properties"]["municipality"]
    assert set(parameter["enum"]) == {"ADM", "AAM", "WRM"}
