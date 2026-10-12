import base64
import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from property_platform.modules.evidence.property_protocol import safe_url, validate_receipts


def receipt(url="https://www.aldar.com/example", payload=b"Reviewed page"):
    now = datetime.now(UTC)
    return {
        "url": url,
        "payload": base64.b64encode(payload).decode(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "http_status": 200,
        "fetched_started_at": (now - timedelta(seconds=1)).isoformat(),
        "fetched_at": now.isoformat(),
    }


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://localhost/x",
        "https://127.0.0.1/x",
        "https://user:pass@www.aldar.com/x",
        "https://www.aldar.com:8000/x",
        "https://host.internal/x",
    ],
)
def test_property_links_reject_unsafe_urls(url):
    assert not safe_url(url)


def test_property_receipt_keeps_actual_bytes_and_timestamps():
    row = receipt()
    result = validate_receipts([row], {row["url"]})[row["url"]]
    assert result["payload"] == b"Reviewed page"
    assert result["fetched_at"].tzinfo is not None
    assert safe_url(row["url"])


@pytest.mark.parametrize("mutation", ["hash", "url", "date", "status", "duplicate", "missing"])
def test_invalid_or_incomplete_property_receipts_are_rejected(mutation):
    row = receipt()
    allowed = {row["url"]}
    rows = [row]
    if mutation == "hash":
        row["sha256"] = "0" * 64
    if mutation == "url":
        row["url"] = "https://unreviewed.example/x"
    if mutation == "date":
        row["fetched_at"] = "2020-01-01T00:00:00"
    if mutation == "status":
        row["http_status"] = 403
    if mutation == "duplicate":
        rows.append(row)
    if mutation == "missing":
        rows.clear()
    with pytest.raises(ValueError):
        validate_receipts(rows, allowed)
