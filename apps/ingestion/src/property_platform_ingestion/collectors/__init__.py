"""Bounded source acquisition; domain validation and persistence belong to the API."""

from .http import Acquisition, AcquisitionError, SourceHTTP
from .map import MapCollector, OnwaniCollector
from .properties import collect_property_receipts
from .references import ReferenceCollector
from .snapshots import (
    ReplayFetcher,
    precollect_map,
    precollect_onwani,
    precollect_reference,
)

__all__ = [
    "Acquisition",
    "AcquisitionError",
    "MapCollector",
    "OnwaniCollector",
    "ReferenceCollector",
    "ReplayFetcher",
    "SourceHTTP",
    "collect_property_receipts",
    "precollect_map",
    "precollect_onwani",
    "precollect_reference",
]
