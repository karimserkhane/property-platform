"""Reviewed public ADREC dashboard protocol. No credentials or private service APIs."""

import hashlib
import json
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

BASE = "https://adrec.gov.ae/api/feature/MarketData/"
PAGE_URL = "https://adrec.gov.ae/en/market-data"
SALES = BASE + "RecentSales"
INDICES = {"sale": BASE + "ResiSalePriceIndexByArea", "rent": BASE + "ResiRentPriceIndexByArea"}
DISTRICTS = {"al-reem-island": "Al Reem Island", "saadiyat-island": "Al Saadiyat Island"}
VERSION = "adrec-public-dashboard-v2"
PAGE_SIZE = 1000
MAX_ROWS = 10000
MAX_BYTES = 8 * 1024 * 1024


class AdrecError(ValueError):
    pass


def sales_scope(territory, *, as_of=None):
    if territory not in DISTRICTS:
        raise AdrecError("Unreviewed ADREC district")
    end = (as_of or datetime.now(ZoneInfo("Asia/Dubai")).date()) - timedelta(days=1)
    start = end - timedelta(days=89)
    return f"{territory}:adrec-sales:{start.isoformat()}:{end.isoformat()}"


def sales_window(scope):
    try:
        territory, name, first, last = scope.split(":")
        start, end = date.fromisoformat(first), date.fromisoformat(last)
        if territory not in DISTRICTS or name != "adrec-sales" or (end - start).days != 89:
            raise AdrecError("Unregistered ADREC sales window")
        if end >= datetime.now(ZoneInfo("Asia/Dubai")).date():
            raise AdrecError("ADREC snapshots use completed calendar days")
        return territory, start, end
    except (AttributeError, ValueError) as exc:
        raise AdrecError("Invalid ADREC snapshot scope") from exc


def sales_windows(scope):
    _, start, end = sales_window(scope)
    return [
        (start + timedelta(days=i), min(end, start + timedelta(days=i + 29))) for i in (0, 30, 60)
    ]


def sales_params(scope, window=None):
    territory, start, end = sales_window(scope)
    first, last = window or sales_windows(scope)[0]
    if (first, last) not in sales_windows(scope) and not (first == last and start <= first <= end):
        raise AdrecError("Unregistered ADREC date partition")
    return dict(
        fromDate=first.isoformat(),
        toDate=last.isoformat(),
        saleApplicationType="all",
        saleSequence="all",
        municipality="all",
        district=DISTRICTS[territory],
        projectName="all",
        assetClass="all",
        propertyType="all",
        page=0,
        size=PAGE_SIZE,
        propertyLayout="all",
        language="en",
    )


def index_params():
    return {"municipality": "all", "district": "all", "language": "en"}


def source_definition(operation, scope):
    if operation == "adrec_sales":
        territory, _, _ = sales_window(scope)
        return (
            f"adrec:market-data:sales:{territory}",
            f"ADREC — {DISTRICTS[territory]} sales",
            SALES,
            VERSION,
        )
    if operation == "adrec_indices" and scope == "abu-dhabi":
        return "adrec:market-data:indices", "ADREC — published price indices", PAGE_URL, VERSION
    raise AdrecError("Unregistered ADREC operation")


def validate_request(operation, scope, url, params):
    values = {key: str(value) for key, value in params.items()}
    if operation == "adrec_sales":
        try:
            window = (date.fromisoformat(values["fromDate"]), date.fromisoformat(values["toDate"]))
        except (ValueError, KeyError) as exc:
            raise AdrecError("Invalid ADREC date partition") from exc
        if url != SALES or values != {k: str(v) for k, v in sales_params(scope, window).items()}:
            raise AdrecError("ADREC request differs from reviewed scope")
    elif operation == "adrec_indices":
        if scope != "abu-dhabi" or url not in INDICES.values() or values != index_params():
            raise AdrecError("Unregistered ADREC index request")
    else:
        raise AdrecError("Unknown ADREC operation")


def decode(payload):
    if len(payload) > MAX_BYTES:
        raise AdrecError("ADREC response exceeds its byte budget")
    try:
        return json.loads(
            payload,
            parse_float=Decimal,
            parse_constant=lambda _: (_ for _ in ()).throw(AdrecError("Non-finite number")),
        )
    except (ValueError, UnicodeError) as exc:
        raise AdrecError("Invalid ADREC JSON") from exc


def page_data(payload, scope, page=0, window=None):
    data = decode(payload)
    if not isinstance(data, dict) or not isinstance(data.get("content"), list):
        raise AdrecError("Unexpected ADREC sales response")
    total = data.get("totalElements")
    if type(total) is not int or not 0 <= total <= MAX_ROWS:
        raise AdrecError("ADREC sales coverage exceeds budget")
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    count = max(0, min(PAGE_SIZE, total - page * PAGE_SIZE))
    if (
        data.get("number") != page
        or data.get("size") != PAGE_SIZE
        or data.get("totalPages") != (0 if total == 0 else pages)
        or len(data["content"]) != count
        or data.get("numberOfElements") != count
    ):
        raise AdrecError("Incomplete or inconsistent ADREC page")
    for row in data["content"]:
        values = sale_record(row, scope)
        if window and not window[0] <= values["registration_date"] <= window[1]:
            raise AdrecError("ADREC ignored the date partition")
    return data["content"], total, pages


def text(row, key):
    value = row.get(key)
    if value is None:
        return ""
    if not isinstance(value, str) or len(value) > 255:
        raise AdrecError("Unexpected ADREC text")
    return value.strip()


def number(row, key, places=8, *, maximum=Decimal("1000000000000000")):
    value = row.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise AdrecError("ADREC numeric type changed")
    try:
        result = Decimal(value)
        if not result.is_finite() or result < 0 or result > maximum:
            raise AdrecError("ADREC number outside documented storage range")
        return result.quantize(Decimal(1).scaleb(-places))
    except InvalidOperation as exc:
        raise AdrecError("Invalid ADREC decimal") from exc


SALE_FIELDS = {
    "asset_class",
    "property_type",
    "sale_application_datetime",
    "property_sold_area_sqm",
    "land_plot_ground_area_sqm",
    "property_layout",
    "district",
    "community",
    "project_name",
    "property_sale_price_aed",
    "property_sold_share",
    "rate_aed_per_sqm",
    "sale_application_type",
    "sale_sequence",
}


def sale_record(row, scope):
    territory, start, end = sales_window(scope)
    if not isinstance(row, dict) or set(row) != SALE_FIELDS:
        raise AdrecError("ADREC sale schema changed")
    try:
        registered = date.fromisoformat(row["sale_application_datetime"])
    except (TypeError, ValueError) as exc:
        raise AdrecError("Unexpected ADREC registration date") from exc
    if not start <= registered <= end or row["district"] != DISTRICTS[territory]:
        raise AdrecError("ADREC row is outside its requested coverage")
    return dict(
        registration_date=registered,
        **{
            key: text(row, key)
            for key in (
                "asset_class",
                "property_type",
                "property_layout",
                "district",
                "community",
                "project_name",
                "sale_application_type",
                "sale_sequence",
            )
        },
        price_aed=number(row, "property_sale_price_aed", 2),
        sold_area_sqm=number(row, "property_sold_area_sqm"),
        plot_area_sqm=number(row, "land_plot_ground_area_sqm"),
        rate_aed_per_sqm=number(row, "rate_aed_per_sqm"),
        sold_share=number(row, "property_sold_share", maximum=Decimal(1)),
    )


def digest(row):
    # Fingerprint is an observation checksum, never an invented transaction identity.
    return hashlib.sha256(json.dumps(row, default=str, sort_keys=True).encode()).hexdigest()


def index_records(payload):
    data = decode(payload)
    fields = {
        "municipality",
        "district",
        "property_type",
        "end_of_period",
        "sale_index_value",
        "index_yoy_change",
    }
    if not isinstance(data, list) or not 1 <= len(data) <= MAX_ROWS:
        raise AdrecError("Unexpected ADREC index coverage")
    output, groups = [], {}
    for row in data:
        if not isinstance(row, dict) or set(row) != fields:
            raise AdrecError("ADREC index schema changed")
        try:
            period = date.fromisoformat(row["end_of_period"])
        except (TypeError, ValueError) as exc:
            raise AdrecError("Invalid index period") from exc
        values = dict(
            municipality=text(row, "municipality"),
            zone_label=text(row, "district"),
            property_type=text(row, "property_type"),
            period_end=period,
            index_value=number(row, "sale_index_value"),
        )
        key = (values["municipality"], values["zone_label"], values["property_type"], period)
        groups.setdefault(key, set()).add(values["index_value"])
        output.append((values, row))
    # Multiple incompatible values with indistinguishable dimensions are not a trustworthy series.
    conflicts = sum(len(values) > 1 for values in groups.values())
    return output, conflicts


def collect_sales(scope, acquire):
    """Full date partitions avoid offset loss when equal-date sales change order."""
    output, count, size = [], 0, 0

    def fetch(window):
        nonlocal size
        payload, receipt = acquire(SALES, sales_params(scope, window))
        size += len(payload)
        if size > 64 * 1024 * 1024:
            raise AdrecError("ADREC acquisition exceeds its total byte budget")
        rows, total, pages = page_data(payload, scope, window=window)
        return payload, receipt, rows, total, pages

    def collect(window):
        nonlocal count
        payload, receipt, rows, total, pages = fetch(window)
        if pages > 1:
            output.append((payload, receipt, []))  # Discovery capture; never counted.
            if window[0] == window[1]:
                raise AdrecError("ADREC daily coverage exceeds a complete response")
            day = window[0]
            while day <= window[1]:
                collect((day, day))
                day += timedelta(days=1)
            return
        final, final_receipt, final_rows, final_total, _ = fetch(window)

        # Flat validated scalars include exact Decimal values. Preserve multiplicity
        # without creating a transaction identity or rounding comparison values.
        if total != final_total or Counter(tuple(sorted(row.items())) for row in rows) != Counter(
            tuple(sorted(row.items())) for row in final_rows
        ):
            raise AdrecError("ADREC date partition changed during acquisition")
        count += total
        if count > MAX_ROWS:
            raise AdrecError("ADREC sales coverage exceeds its total row budget")
        output.extend([(payload, receipt, rows), (final, final_receipt, [])])

    for window in sales_windows(scope):
        collect(window)
    return output, count
