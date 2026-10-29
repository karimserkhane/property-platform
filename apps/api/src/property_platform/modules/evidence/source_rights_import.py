"""Mirror the reviewed source rights and their enforcement; history is revoked, not lost."""

from datetime import date

from django.db import transaction
from django.utils import timezone

from . import source_rights as rights
from .rights_models import SourceRights, SourceRightsEnforcement

FIELDS = (
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
)
DECISION = ("enforced", "decided_on", "decided_by", "basis")
REVISED = "Superseded by a revised source rights review"
REMOVED = "Removed from the reviewed source rights registry"
REDECIDED = "Superseded by a revised enforcement decision"


def apply_source_rights(*, actor):
    """Create, keep or revoke one active row per reviewed host and per right, idempotently.

    The repository files stay the reviewed truth; these tables record which review and
    which enforcement decision were in force when, for audit and for SQL that joins
    rights to captures by host (`evidence.data_rights`, A23).
    """
    actor = actor.strip()
    if not 1 <= len(actor) <= 160:
        raise ValueError("Valid source rights actor required")
    summary = {"created": 0, "kept": 0, "revoked": 0}
    with transaction.atomic():
        current = {
            row.host: row for row in SourceRights.objects.select_for_update().filter(active=True)
        }
        for review in rights.source_rights():
            values = _dated(review, FIELDS, "reviewed_on")
            row = current.pop(review["host"], None)
            if row is not None and all(getattr(row, key) == value for key, value in values.items()):
                summary["kept"] += 1
                continue
            if row is not None:
                _revoke(row, actor, REVISED)
                summary["revoked"] += 1
            SourceRights.objects.create(host=review["host"], actor=actor, **values)
            summary["created"] += 1
        for row in current.values():
            _revoke(row, actor, REMOVED)
            summary["revoked"] += 1
        summary["enforcement"] = _apply_enforcement(actor)
    return summary


def _apply_enforcement(actor):
    summary = {"created": 0, "kept": 0, "revoked": 0}
    current = {
        row.name: row
        for row in SourceRightsEnforcement.objects.select_for_update().filter(active=True)
    }
    for right, decision in rights.enforcement().items():
        values = _dated(decision, DECISION, "decided_on")
        row = current.pop(right, None)
        if row is not None and all(getattr(row, key) == value for key, value in values.items()):
            summary["kept"] += 1
            continue
        if row is not None:
            _revoke(row, actor, REDECIDED)
            summary["revoked"] += 1
        SourceRightsEnforcement.objects.create(name=right, actor=actor, **values)
        summary["created"] += 1
    return summary


def _dated(source, fields, date_field):
    values = {key: source[key] for key in fields}
    if values[date_field] is not None:
        values[date_field] = date.fromisoformat(values[date_field])
    return values


def _revoke(row, actor, reason):
    row.active = False
    row.revoked_at = timezone.now()
    row.revoked_by = actor
    row.revocation_reason = reason
    row.save(update_fields=["active", "revoked_at", "revoked_by", "revocation_reason"])
