"""Capture registered public research pages without treating them as approved facts."""

from collections.abc import Sequence

from .http import AcquisitionError, SourceHTTP, checked_url

MAX_REFERENCE_BYTES = 4 * 1024 * 1024
SOURCE_KINDS = frozenset({"authority", "developer", "broker", "forum", "media"})


def selected_references(rows: Sequence[dict], *, limit: int = 200, kind: str | None = None):
    """Stable reviewed registry order; no arbitrary URL filter or fetched discovery."""
    if type(limit) is not int or not 1 <= limit <= 200:
        raise AcquisitionError("Reference limit must be between 1 and 200")
    if kind is not None and kind not in SOURCE_KINDS:
        raise AcquisitionError("Unknown research source kind")
    if not isinstance(rows, (list, tuple)) or not 1 <= len(rows) <= 200:
        raise AcquisitionError("Research registry must contain 1–200 reviewed entries")
    checked, seen = [], set()
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != {"url", "label", "kind"}
            or not isinstance(row["label"], str)
            or not 1 <= len(row["label"].strip()) <= 255
            or row["kind"] not in SOURCE_KINDS
        ):
            raise AcquisitionError("Unexpected research registry entry")
        url = checked_url(row["url"])
        if url in seen:
            raise AcquisitionError("Duplicate research source URL")
        seen.add(url)
        if kind is None or row["kind"] == kind:
            checked.append(dict(row))
    return checked[:limit]


class ReferenceCollector:
    def __init__(self, client: SourceHTTP, registry_rows: Sequence[dict]):
        self.client = client
        self._rows = {row["url"]: row for row in selected_references(registry_rows)}

    @staticmethod
    def allowed_urls(rows: Sequence[dict]) -> tuple[str, ...]:
        return tuple(row["url"] for row in selected_references(rows))

    def fetch(self, row: dict) -> tuple[bytes, dict]:
        if not isinstance(row, dict) or self._rows.get(row.get("url")) != row:
            raise AcquisitionError("Research source is not an exact registered entry")
        return self.fetch_url(row["url"])

    def fetch_url(self, url: str) -> tuple[bytes, dict]:
        if url not in self._rows:
            raise AcquisitionError("Research source URL is not registered")
        acquisition = self.client.fetch(url, max_bytes=MAX_REFERENCE_BYTES)
        return acquisition.payload, acquisition.capture_receipt()
