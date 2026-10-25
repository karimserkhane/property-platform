"""Make active ADREC market labels follow the reviewed file; history is revoked, not lost."""

from datetime import date

from django.db import transaction
from django.utils import timezone

from property_platform.modules.catalog.models import Project

from .project_models import ProjectMarketLabel
from .project_protocol import project_market_labels

REVOCATION_REASON = "Removed from the reviewed market label registry"


def apply_project_market_labels(*, territory=None, actor):
    """Create, keep or revoke labels for one territory (or all), idempotently.

    A label waits until its project exists; the catalogue pipelines create it, so a
    rebuild from archives restores every link. Sales are matched at read time, so a
    label may precede the first ADREC snapshot that contains it.
    """
    actor = actor.strip()
    if not 1 <= len(actor) <= 160:
        raise ValueError("Valid market label actor required")
    rows = project_market_labels(territory)
    projects = {
        project.slug: project
        for project in Project.objects.filter(slug__in={row["project"] for row in rows})
    }
    summary = {"created": 0, "kept": 0, "revoked": 0, "waiting": 0}
    with transaction.atomic():
        wanted = set()
        for row in rows:
            project = projects.get(row["project"])
            if project is None:
                summary["waiting"] += 1
                continue
            values = {
                "project": project,
                "evidence": row["evidence"],
                "registration_number": row.get("registration_number", ""),
                "basis": row["basis"],
                "reviewed_on": date.fromisoformat(row["reviewed_on"]),
            }
            current = (
                ProjectMarketLabel.objects.select_for_update()
                .filter(district=row["district"], label=row["label"], active=True)
                .first()
            )
            if current is not None and all(
                getattr(current, key) == value for key, value in values.items()
            ):
                wanted.add(current.pk)
                summary["kept"] += 1
                continue
            if current is not None:
                _revoke(current, actor, "Superseded by a revised reviewed market label")
                summary["revoked"] += 1
            label = ProjectMarketLabel.objects.create(
                district=row["district"], label=row["label"], actor=actor, **values
            )
            wanted.add(label.pk)
            summary["created"] += 1
        stale = ProjectMarketLabel.objects.select_for_update().filter(active=True)
        if territory:
            stale = stale.filter(project__territory_id=territory.split(":")[0])
        for label in stale.exclude(pk__in=wanted):
            _revoke(label, actor, REVOCATION_REASON)
            summary["revoked"] += 1
    return summary


def _revoke(label, actor, reason):
    label.active = False
    label.revoked_at = timezone.now()
    label.revoked_by = actor
    label.revocation_reason = reason
    label.save(update_fields=["active", "revoked_at", "revoked_by", "revocation_reason"])
