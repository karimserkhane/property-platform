"""Reviewed rights of every source site: what may be collected and what may be shown (A19).

Rights belong to the publisher of a site (or one of its hosts), not to each row: every
capture, observation and fact inherits them through the URL it was read from, so a
revised review applies to all past and future data at once. The registry is the
single reviewed truth; `source_rights_import.py` mirrors it, with its history, into
`evidence.source_rights` for audit and SQL. No network, ORM or Django setting is
needed here, so ingestion and the API share this module.

- `collection`: `allowed`, or `forbidden` when the site's terms forbid automated
  access. Pipelines and registries stay; collectors simply skip the site.
- `publication`: `open` (licensed for redistribution, with its attribution), `facts`
  (dated facts with a short original quote and a link to the page), `link` (a plain
  link only) or `none`.

Whether each right is applied is a separate owner decision (A22), one switch per
right in `source_rights_enforcement.json`: rights stay recorded and reported either
way, and switching one on applies it to every source at once. A forbidden or
withheld site keeps its private receipts, which replay exactly; when publication is
enforced, the read models apply its level to them as to new data.
"""

import json
import re
from datetime import date
from functools import cache
from pathlib import Path
from urllib.parse import urlsplit

REGISTRY = Path(__file__).parent / "source_rights.json"
ENFORCEMENT = Path(__file__).parent / "source_rights_enforcement.json"
RIGHTS = ("collection", "publication")
COLLECTION = ("allowed", "forbidden")
PUBLICATION = ("open", "facts", "link", "none")
FACTS = frozenset({"open", "facts"})
UNKNOWN = "unknown"
CLOSED_LICENCES = frozenset({UNKNOWN, "proprietary"})
_HOST = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+(?:-[a-z0-9]+)*)+")
_FIELDS = {
    "host",
    "publisher",
    "licence",
    "licence_url",
    "terms_url",
    "reviewed_on",
    "reviewed_by",
    "collection",
    "publication",
    "attribution",
    "basis",
}
_DECISION = {"enforced", "decided_on", "decided_by", "basis"}
# A host nobody reviewed keeps the private-preview treatment, marked as unqualified.
DEFAULT = {
    "host": None,
    "publisher": "",
    "licence": UNKNOWN,
    "licence_url": "",
    "terms_url": "",
    "reviewed_on": None,
    "reviewed_by": "",
    "collection": "allowed",
    "publication": "facts",
    "attribution": "",
    "basis": "Not in the reviewed source rights registry.",
}


def _https(value):
    return value == "" or (isinstance(value, str) and value.startswith("https://"))


def validate_source_rights(rows):
    if not isinstance(rows, list):
        raise ValueError("Expected a list of reviewed source rights")
    hosts = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != _FIELDS:
            raise ValueError("Unexpected source rights entry")
        host = row["host"]
        if not isinstance(host, str) or not _HOST.fullmatch(host) or host.startswith("www."):
            raise ValueError("Source rights name a host, without www.")
        if host in hosts:
            raise ValueError("Duplicate source rights host")
        hosts.add(host)
        for key, limit in (("publisher", 160), ("licence", 80), ("basis", 500)):
            if not isinstance(row[key], str) or not row[key].strip() or len(row[key]) > limit:
                raise ValueError("Source rights need a publisher, a licence and their basis")
        if not all(_https(row[key]) for key in ("licence_url", "terms_url")):
            raise ValueError("Licence and terms links are HTTPS pages")
        if row["collection"] not in COLLECTION or row["publication"] not in PUBLICATION:
            raise ValueError("Unknown collection or publication right")
        if not isinstance(row["attribution"], str) or len(row["attribution"]) > 300:
            raise ValueError("Unexpected attribution")
        if row["reviewed_on"] is None:
            if row["licence"] != UNKNOWN or row["reviewed_by"] or row["collection"] != "allowed":
                raise ValueError("Only a review can set a licence or forbid collection")
        else:
            date.fromisoformat(row["reviewed_on"])
            if not isinstance(row["reviewed_by"], str) or not row["reviewed_by"].strip():
                raise ValueError("A review names who made it")
        if row["collection"] == "forbidden" and not row["terms_url"]:
            raise ValueError("A forbidden collection cites the terms that forbid it")
        if row["publication"] == "open" and (
            row["licence"] in CLOSED_LICENCES or not row["attribution"].strip()
        ):
            raise ValueError("Open publication needs an open licence and its attribution")
    # A host inside another listed one would be a second, contradictory review.
    if any(host.endswith("." + other) for host in hosts for other in hosts):
        raise ValueError("Source rights hosts must not nest")
    return rows


def validate_enforcement(decisions):
    if not isinstance(decisions, dict) or set(decisions) != set(RIGHTS):
        raise ValueError("Enforcement decides collection and publication")
    for decision in decisions.values():
        if not isinstance(decision, dict) or set(decision) != _DECISION:
            raise ValueError("Unexpected enforcement decision")
        if not isinstance(decision["enforced"], bool):
            raise ValueError("A right is enforced or not")
        if not isinstance(decision["decided_on"], str):
            raise ValueError("An enforcement decision is dated")
        date.fromisoformat(decision["decided_on"])
        for key, limit in (("decided_by", 80), ("basis", 500)):
            if not isinstance(decision[key], str) or not decision[key].strip():
                raise ValueError("An enforcement decision names who made it and why")
            if len(decision[key]) > limit:
                raise ValueError("Enforcement decision too long")
    return decisions


@cache
def source_rights():
    """The reviewed rights, validated once per process."""
    return tuple(validate_source_rights(json.loads(REGISTRY.read_text("utf-8"))))


@cache
def enforcement():
    """The owner's decision for each right, validated once per process."""
    return validate_enforcement(json.loads(ENFORCEMENT.read_text("utf-8")))


def enforced(right):
    return enforcement()[right]["enforced"]


def rights_for(url):
    """The reviewed rights covering `url` (its host or a subdomain), else `DEFAULT`."""
    try:
        host = (urlsplit(url).hostname or "").lower()
    except AttributeError, TypeError, ValueError:
        return DEFAULT
    for row in source_rights():
        if host == row["host"] or host.endswith("." + row["host"]):
            return row
    return DEFAULT


def collection_allowed(url):
    return not enforced("collection") or rights_for(url)["collection"] == "allowed"


def facts_allowed(url):
    """Facts read from this page may be shown, with their source."""
    return not enforced("publication") or rights_for(url)["publication"] in FACTS


def link_allowed(url):
    """A plain link to this page may be shown."""
    return not enforced("publication") or rights_for(url)["publication"] != "none"


def public_rights(url):
    """What a reader is told about the rights of a source page.

    `shown_beyond_terms` flags data shown only because publication is not enforced
    (A22): its site's terms allow a plain link (`link`) or nothing (`none`).
    """
    row = rights_for(url)
    return {
        "licence": row["licence"],
        "licence_url": row["licence_url"] or None,
        "terms_url": row["terms_url"] or None,
        "publication": row["publication"],
        "attribution": row["attribution"] or None,
        "reviewed_on": row["reviewed_on"],
        "shown_beyond_terms": not enforced("publication") and row["publication"] not in FACTS,
    }


def withheld_capture_pattern():
    """Case-insensitive PostgreSQL regex for captures whose facts are withheld, or None.

    Capture URLs are explicit HTTPS URLs without credentials (`checked_url`), so the
    authority is a host with an optional :443 port.
    """
    if not enforced("publication"):
        return None
    hosts = "|".join(
        re.escape(row["host"]) for row in source_rights() if row["publication"] not in FACTS
    )
    return rf"^https://([^/?#:]+\.)?({hosts})(:443)?([/?#]|$)" if hosts else None
