"""Owner decisions withdrawing whole sites: never collected again, never published (A19).

A withdrawn site keeps its registry entries and private receipts, so a rebuild replays
history exactly as it was recorded. Collectors skip it and read models hide every fact,
position or link its captures support. Removing an entry restores both. No network,
ORM or Django setting is needed, so ingestion and the API share this module.
"""

import json
import re
from datetime import date
from functools import cache
from pathlib import Path
from urllib.parse import urlsplit

REGISTRY = Path(__file__).parent / "source_withdrawals.json"
_HOST = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+(?:-[a-z0-9]+)*)+")
_FIELDS = {"host", "publisher", "decided_on", "decided_by", "reason", "links"}


def validate_withdrawals(rows):
    if not isinstance(rows, list):
        raise ValueError("Expected a list of reviewed site withdrawals")
    hosts = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != _FIELDS:
            raise ValueError("Unexpected site withdrawal entry")
        host = row["host"]
        if not isinstance(host, str) or not _HOST.fullmatch(host) or host.startswith("www."):
            raise ValueError("A withdrawal names a registrable host, without www.")
        if host in hosts:
            raise ValueError("Duplicate site withdrawal")
        hosts.add(host)
        for key, limit in (("publisher", 160), ("decided_by", 160), ("reason", 500)):
            if not isinstance(row[key], str) or not row[key].strip() or len(row[key]) > limit:
                raise ValueError("A withdrawal needs its publisher, decision maker and reason")
        date.fromisoformat(row["decided_on"])
        if type(row["links"]) is not bool:
            raise ValueError("A withdrawal states whether plain links remain allowed")
    # A host inside another withdrawn one would be a second, contradictory decision.
    if any(host.endswith("." + other) for host in hosts for other in hosts):
        raise ValueError("A withdrawal must not cover another withdrawn host")
    return rows


@cache
def withdrawals():
    """The reviewed decisions, validated once per process."""
    return tuple(validate_withdrawals(json.loads(REGISTRY.read_text("utf-8"))))


def withdrawal(url):
    """The decision covering `url` (its host or any subdomain), or None."""
    try:
        host = (urlsplit(url).hostname or "").lower()
    except AttributeError, TypeError, ValueError:
        return None
    for row in withdrawals():
        if host == row["host"] or host.endswith("." + row["host"]):
            return row
    return None


def is_withdrawn(url):
    return withdrawal(url) is not None


def link_allowed(url):
    """A plain link to the page stays possible only where the decision allows it."""
    row = withdrawal(url)
    return row is None or row["links"]


def capture_url_pattern():
    """Case-insensitive PostgreSQL regex for capture URLs of withdrawn sites, or None.

    Capture URLs are explicit HTTPS URLs without credentials (`checked_url`), so the
    authority is a host with an optional :443 port.
    """
    hosts = "|".join(re.escape(row["host"]) for row in withdrawals())
    return rf"^https://([^/?#:]+\.)?({hosts})(:443)?([/?#]|$)" if hosts else None
