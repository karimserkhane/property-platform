"""Inert validation of bounded, explicit acquisition receipts and licensed media."""

import base64
import hashlib
import html
import ipaddress
from datetime import UTC, datetime
from urllib.parse import urlparse

MAX_CAPTURE_BYTES = 4 * 1024 * 1024
MAX_IMAGE_BYTES = 2 * 1024 * 1024
LICENCES = {
    "CC-BY-3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
}


def safe_url(value):
    try:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return False
        if parsed.port not in (None, 443) or "." not in parsed.hostname:
            return False
        try:
            ipaddress.ip_address(parsed.hostname)
            return False
        except ValueError:
            return not parsed.hostname.endswith((".local", ".localhost", ".internal"))
    except TypeError, ValueError:
        return False


def validate_receipts(rows, allowed_urls):
    result = {}
    for row in rows:
        url = row["url"]
        if url not in allowed_urls or url in result or row["http_status"] != 200:
            raise ValueError("Unexpected or unsuccessful property receipt")
        payload = base64.b64decode(row["payload"], validate=True)
        started, fetched = (
            datetime.fromisoformat(row[key]) for key in ("fetched_started_at", "fetched_at")
        )
        if (
            not started.tzinfo
            or not fetched.tzinfo
            or started > fetched
            or fetched > datetime.now(UTC)
        ):
            raise ValueError("Invalid acquisition times")
        if (
            not payload
            or len(payload) > MAX_CAPTURE_BYTES
            or hashlib.sha256(payload).hexdigest() != row["sha256"]
        ):
            raise ValueError("Invalid property receipt hash or size")
        result[url] = {
            **row,
            "payload": payload,
            "fetched_started_at": started,
            "fetched_at": fetched,
        }
    if set(result) != allowed_urls:
        raise ValueError("Incomplete property acquisition")
    return result


def validate_photo(photo, receipts):
    licence = LICENCES.get(photo["licence_code"])
    if licence != photo["licence_url"] or not safe_url(photo["image_url"]):
        raise ValueError("Image licence not approved")
    if (
        urlparse(photo["image_url"]).hostname != "upload.wikimedia.org"
        or urlparse(photo["source_url"]).hostname != "commons.wikimedia.org"
    ):
        raise ValueError("Unexpected image provider")
    text = html.unescape(receipts[photo["source_url"]]["payload"].decode("utf-8", errors="replace"))
    if licence.rstrip("/") not in text or photo["author"].lower() not in text.lower():
        raise ValueError("Image author/licence not present in captured source")
    payload = receipts[photo["image_url"]]["payload"]
    if (
        len(payload) > MAX_IMAGE_BYTES
        or photo["mime_type"] != "image/jpeg"
        or not payload.startswith(b"\xff\xd8\xff")
    ):
        raise ValueError("Unexpected image bytes")
