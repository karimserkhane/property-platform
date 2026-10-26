import json
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from property_platform.modules.evidence.sources import adrec

from property_platform_ingestion import flows
from property_platform_ingestion.collectors.adrec import precollect_adrec


def acquired(payload):
    return SimpleNamespace(
        payload=payload, http_status=200, capture_receipt=lambda: {"fetched_at": "original-clock"}
    )


def empty_page():
    return json.dumps(
        {
            "content": [],
            "totalElements": 0,
            "number": 0,
            "size": adrec.PAGE_SIZE,
            "numberOfElements": 0,
            "totalPages": 0,
        }
    ).encode()


def test_precollection_replays_both_identical_requests_without_network():
    scope = adrec.sales_scope("al-reem-island", as_of=date(2026, 10, 13))
    transport = Mock(fetch=Mock(return_value=acquired(empty_page())))
    replay = precollect_adrec(transport, "adrec_sales", scope)
    assert transport.fetch.call_count == 6
    for window in adrec.sales_windows(scope):
        for _ in range(2):
            assert (
                replay.map(adrec.SALES, adrec.sales_params(scope, window))[1]["fetched_at"]
                == "original-clock"
            )
    replay.assert_consumed()
    assert transport.fetch.call_count == 6


def test_changed_page_is_not_materialised():
    scope = adrec.sales_scope("al-reem-island", as_of=date(2026, 10, 13))
    transport = Mock(fetch=Mock(side_effect=[acquired(empty_page()), acquired(b"{}")]))
    with pytest.raises(adrec.AdrecError):
        precollect_adrec(transport, "adrec_sales", scope)


def test_scheduled_time_fixes_scope_to_dubai_calendar(monkeypatch):
    monkeypatch.setattr(
        flows.flow_run, "scheduled_start_time", datetime(2026, 10, 12, 22, tzinfo=UTC)
    )
    invoke = Mock(return_value={"status": "succeeded"})
    monkeypatch.setattr(flows, "ingest_source", invoke)
    flows.adrec_sales.fn(territory="saadiyat-island", actor="test")
    invoke.assert_called_once_with(
        "adrec_sales", "saadiyat-island:adrec-sales:2026-07-15:2026-10-12", "test"
    )
