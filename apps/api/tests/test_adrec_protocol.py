import json
from datetime import date
from decimal import Decimal

import pytest

from property_platform.modules.evidence.sources import adrec

SCOPE = adrec.sales_scope("al-reem-island", as_of=date(2026, 10, 13))


def sale():
    return {
        "asset_class": "residential",
        "property_type": "apartment",
        "sale_application_datetime": "2026-10-12",
        "property_sold_area_sqm": 100.25,
        "land_plot_ground_area_sqm": None,
        "property_layout": "2 beds",
        "district": "Al Reem Island",
        "community": "RT3",
        "project_name": "Example Project",
        "property_sale_price_aed": 1900000.12,
        "property_sold_share": 1,
        "rate_aed_per_sqm": 18952.61965087,
        "sale_application_type": "off-plan",
        "sale_sequence": "primary",
    }


def page(rows, *, total=None, number=0):
    total = len(rows) if total is None else total
    return json.dumps(
        {
            "content": rows,
            "totalElements": total,
            "number": number,
            "size": adrec.PAGE_SIZE,
            "totalPages": (total + adrec.PAGE_SIZE - 1) // adrec.PAGE_SIZE,
            "numberOfElements": len(rows),
        }
    ).encode()


def index(value=100):
    return {
        "municipality": "Abu Dhabi City",
        "district": "(all zones)",
        "property_type": "apartments & duplexes",
        "end_of_period": "2026-08-31",
        "sale_index_value": value,
        "index_yoy_change": None,
    }


def test_exact_scope_and_decimal_preservation():
    assert SCOPE.endswith(":2026-07-15:2026-10-12")
    record = adrec.sale_record(adrec.decode(page([sale()]))["content"][0], SCOPE)
    assert record["price_aed"] == Decimal("1900000.12")
    assert record["sold_area_sqm"] == Decimal("100.25000000")
    assert record["plot_area_sqm"] is None
    with pytest.raises(adrec.AdrecError):
        adrec.validate_request(
            "adrec_sales", SCOPE, adrec.SALES, {**adrec.sales_params(SCOPE), "district": "Dubai"}
        )


@pytest.mark.parametrize(
    "change",
    [
        {"property_sold_share": 1.1},
        {"property_sale_price_aed": -1},
        {"sale_application_datetime": "2026-01-01"},
        {"transaction_id": "invented"},
    ],
)
def test_changed_schema_or_out_of_scope_rows_fail_closed(change):
    with pytest.raises(adrec.AdrecError):
        adrec.page_data(page([{**sale(), **change}]), SCOPE, 0)


def test_full_date_partitions_keep_duplicates_and_allow_reordering():
    rows = [sale(), sale(), {**sale(), "project_name": "Other Project"}]
    responses = iter([(page([]), {})] * 4 + [(page(rows), {}), (page(list(reversed(rows))), {})])
    pages, count = adrec.collect_sales(SCOPE, lambda *_: next(responses))
    assert count == 3 and sum(len(rows) for _, _, rows in pages) == 3
    responses = iter([(page([]), {})] * 4 + [(page(rows), {}), (page([sale()] * 3), {})])
    with pytest.raises(adrec.AdrecError, match="changed"):
        adrec.collect_sales(SCOPE, lambda *_: next(responses))


def test_overfull_month_is_partitioned_by_day_without_offset_pages():
    def acquire(url, params):
        first, last = params["fromDate"], params["toDate"]
        row = {**sale(), "sale_application_datetime": first}
        if first != last and first == "2026-07-15":
            return page([row] * 1000, total=1001), {}
        count = (
            501 if first == last == "2026-07-15" else 500 if first == last == "2026-07-16" else 0
        )
        return page([row] * count), {}

    pages, count = adrec.collect_sales(SCOPE, acquire)
    assert count == 1001 and sum(len(rows) for _, _, rows in pages) == count


def test_conflicting_indistinguishable_index_series_are_identified():
    rows, conflicts = adrec.index_records(json.dumps([index(100), index(110)]).encode())
    assert len(rows) == 2 and conflicts == 1
    assert adrec.index_records(json.dumps([index(), index()]).encode())[1] == 0


def test_partial_pages_and_nonfinite_values_are_rejected():
    with pytest.raises(adrec.AdrecError):
        adrec.page_data(page([sale()], total=101), SCOPE, 0)
    with pytest.raises(adrec.AdrecError):
        adrec.decode(b'{"value": NaN}')
