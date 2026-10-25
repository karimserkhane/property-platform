"""Acquisition callables of the construction activity operation (B06).

The evidence operation decides which parcels to measure and stores captures and
results; this collector searches scenes, reads parcel windows and computes the change
signal from the captured window bytes, so a stored result is replayable from captures.
"""

from datetime import UTC, datetime

import numpy as np

from .http import SourceHTTP
from .sentinel_activity import (
    BANDS,
    CLASSIFICATION,
    METHOD_VERSION,
    change_signal,
    select_scenes,
)
from .sentinel_windows import (
    SEARCH_URL,
    RangeSession,
    WindowError,
    decode_window,
    encode_window,
    parcel_mask,
    read_window,
    search_page,
    search_scenes,
)


class ActivityCollector:
    """One measuring session: a paginated STAC search, then bounded parcel windows.

    ``search_transport`` and ``range_transport`` enable network-free tests.
    """

    method_version = METHOD_VERSION

    def __init__(self, *, end=None, search_transport=None, range_transport=None):
        self.end = end or datetime.now(UTC)
        self._http = SourceHTTP([SEARCH_URL], transport=search_transport, total_timeout_seconds=300)
        self._ranges = RangeSession(transport=range_transport)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._ranges.close()
        self._http.close()

    def scenes(self, bbox):
        """Search pages with their receipts and the selected scenes, oldest first per tile.

        Each scene names the index of the page that listed it, so its window capture can
        cite that page.
        """
        before = len(self._http.acquisitions)
        features = search_scenes(self._http, bbox, end=self.end)
        pages, page_of = [], {}
        for index, acquisition in enumerate(self._http.acquisitions[before:]):
            pages.append({"payload": acquisition.payload, "receipt": acquisition.capture_receipt()})
            for feature in search_page(acquisition.payload)[0]:
                page_of.setdefault(feature["id"], index)
        scenes = [scene | {"page": page_of[scene["scene_id"]]} for scene in select_scenes(features)]
        return {"pages": pages, "scenes": scenes}

    def window(self, scene, geometry):
        """Capture bytes and receipt of one parcel window.

        None when the parcel cannot be read on this scene (outside its tile or larger
        than a window); transport and budget failures still raise.
        """
        try:
            window = read_window(scene, geometry, open_asset=self._ranges.open)
        except WindowError:
            return None
        return {
            "payload": encode_window(window),
            "receipt": {
                "url": window["item_url"],
                "fetched_started_at": window["fetched_started_at"],
                "fetched_at": window["fetched_at"],
                "http_status": 206,
                "acquisition_method": "sentinel_cog_window_ranges",
                "timestamp_basis": "collector_clock",
            },
        }

    @staticmethod
    def signal(before_payload, after_payload, geometry):
        """Change signal of two captured windows of one parcel, from capture bytes only."""
        return replay_signal(before_payload, after_payload, geometry)


def replay_signal(before_payload, after_payload, geometry):
    """Recompute a stored measurement from its two window captures, without network."""
    before, after = decode_window(before_payload), decode_window(after_payload)
    if (
        before["tile"] != after["tile"]
        or before["crs"] != after["crs"]
        or before["shape"] != after["shape"]
        or not np.allclose(before["transform"], after["transform"], rtol=0, atol=1e-6)
    ):
        raise WindowError("Windows of one parcel must share one grid")
    mask = parcel_mask(geometry, before)
    values = [
        {key: window["values"][key] for key in (*BANDS, CLASSIFICATION)}
        for window in (before, after)
    ]
    return change_signal(*values, mask)
