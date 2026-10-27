"""Mirror the reviewed source rights into `evidence.source_rights`; history is revoked, not lost."""

from datetime import date

from django.db import transaction
from django.utils import timezone

from . import source_rights as rights
from .rights_models import SourceRights

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
REVISED = "Superseded by a revised source rights review"
REMOVED = "Removed from the reviewed source rights registry"


def apply_source_rights(*, actor):
    """Create, keep or revoke one active row per reviewed host, idempotently.

    The repository file stays the reviewed truth; this table records which review was
    in force when, for audit and for SQL that joins rights to captures by host.
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
            values = {key: review[key] for key in FIELDS}
            if values["reviewed_on"] is not None:
                values["reviewed_on"] = date.fromisoformat(values["reviewed_on"])
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
    return summary


def _revoke(row, actor, reason):
    row.active = False
    row.revoked_at = timezone.now()
    row.revoked_by = actor
    row.revocation_reason = reason
    row.save(update_fields=["active", "revoked_at", "revoked_by", "revocation_reason"])
