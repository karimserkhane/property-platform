import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from property_platform.modules.evidence.sources import abu_dhabi

from property_platform_ingestion import flows
from property_platform_ingestion.collectors.context import precollect_context


def response(payload, status=200):
    return SimpleNamespace(
        payload=payload, http_status=status, capture_receipt=lambda: {"fetched_at": "original-time"}
    )


def test_context_collects_once_then_replays_exact_original_response():
    body = json.dumps(
        [
            {
                "FacilityID": 1,
                "FacilityName": "Hospital",
                "FacilityType": "Hospital",
                "IsPlannedProperty": False,
                "Longitude": 54.4,
                "Latitude": 24.5,
            }
        ]
    ).encode()
    transport = Mock(fetch=Mock(return_value=response(body)))
    replay = precollect_context(transport, "abu-dhabi:health")
    payload, receipt = replay.map(abu_dhabi.FEEDS["health"].url, {})
    assert payload == body and receipt["fetched_at"] == "original-time"
    replay.assert_consumed()
    transport.fetch.assert_called_once()


@pytest.mark.parametrize("body,status", [(b"{}", 200), (b"unauthorized", 401)])
def test_incomplete_or_refused_feed_never_becomes_a_replay(body, status):
    with pytest.raises(abu_dhabi.ContextError):
        precollect_context(
            Mock(fetch=Mock(return_value=response(body, status))), "abu-dhabi:health"
        )


def test_flow_uses_fixed_authority_scope(monkeypatch):
    invoke = Mock()
    monkeypatch.setattr(flows, "ingest_source", invoke)
    flows.public_context.fn(dataset="schools", territory="abu-dhabi", actor="test")
    invoke.assert_called_once_with("public_context", "abu-dhabi:schools", "test")
