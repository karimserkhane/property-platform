"""Acquire only source/photograph URLs referenced by reviewed property identities."""

import json
from collections.abc import Sequence

from property_platform.modules.evidence.property_protocol import (
    MAX_CAPTURE_BYTES,
    MAX_IMAGE_BYTES,
    validate_photo,
    validate_receipts,
)

from .http import AcquisitionError, SourceHTTP, checked_url

MAX_PROPERTY_RECEIPT_BYTES = 32 * 1024 * 1024


def property_urls(profiles: Sequence[dict], photos: dict) -> tuple[str, ...]:
    """Preserve source order and deduplicate transport, never merge domain identities."""
    if not isinstance(profiles, (list, tuple)) or not 1 <= len(profiles) <= 200:
        raise AcquisitionError("Property registry must contain 1–200 reviewed identities")
    if not isinstance(photos, dict) or len(photos) > 200:
        raise AcquisitionError("Unexpected photograph registry")
    urls = []
    try:
        for profile in profiles:
            urls.append(checked_url(profile["source_url"]))
            if key := profile.get("photo_key"):
                photo = photos[key]
                urls.extend((checked_url(photo["source_url"]), checked_url(photo["image_url"])))
    except (KeyError, TypeError) as exc:
        raise AcquisitionError("Incomplete property acquisition registry") from exc
    return tuple(dict.fromkeys(urls))


def collect_property_receipts(
    client: SourceHTTP,
    profiles: Sequence[dict],
    photos: dict,
    *,
    max_receipt_bytes: int = MAX_PROPERTY_RECEIPT_BYTES,
) -> list[dict]:
    """Return a complete fresh batch or fail, never import a partial/stale receipt file."""
    urls = property_urls(profiles, photos)
    if (
        type(max_receipt_bytes) is not int
        or not 1 <= max_receipt_bytes <= MAX_PROPERTY_RECEIPT_BYTES
    ):
        raise AcquisitionError("Invalid property receipt batch byte budget")
    image_urls = {photos[row["photo_key"]]["image_url"] for row in profiles if row.get("photo_key")}
    receipts, total_size = [], 2
    for url in urls:
        row = client.fetch(
            url, max_bytes=MAX_IMAGE_BYTES if url in image_urls else MAX_CAPTURE_BYTES
        ).property_receipt()
        # Count the actual JSON/base64 receipt before collecting another URL, rather
        # than buffering up to 200 full-sized responses before checkpoint validation.
        total_size += len(json.dumps(row).encode()) + (2 if receipts else 0)
        if total_size > max_receipt_bytes:
            raise AcquisitionError("Property acquisition exceeds its receipt batch byte budget")
        receipts.append(row)
    # Reuse the inert API protocol for exact bytes/hash, chronology and photo licence.
    verified = validate_receipts(receipts, set(urls))
    for row in profiles:
        if row.get("photo_key"):
            validate_photo(photos[row["photo_key"]], verified)
    return receipts
