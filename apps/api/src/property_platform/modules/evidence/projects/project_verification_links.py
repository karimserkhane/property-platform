"""Make active verification links follow the reviewed file; history is revoked, not lost."""

from datetime import date

from django.db import transaction
from django.utils import timezone

from property_platform.modules.catalog.models import Project

from ..project_models import ProjectVerificationLink
from .project_protocol import project_verification_links

AUTHORITY = "adrec"
REVOCATION_REASON = "Removed from the reviewed verification link registry"


def apply_project_verification_links(*, territory=None, actor):
    """Create, keep or revoke links for one territory (or all), idempotently.

    A link waits until its project exists; the catalogue pipelines create it, so a
    rebuild from archives restores every link without reading the verification page.
    """
    actor = actor.strip()
    if not 1 <= len(actor) <= 160:
        raise ValueError("Valid verification link actor required")
    rows = project_verification_links(territory)
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
            reviewed_on = date.fromisoformat(row["reviewed_on"])
            current = (
                ProjectVerificationLink.objects.select_for_update()
                .filter(
                    project=project,
                    authority=AUTHORITY,
                    registration_number=row["registration_number"],
                    active=True,
                )
                .first()
            )
            if current is not None and (current.url, current.basis, current.reviewed_on) == (
                row["url"],
                row["basis"],
                reviewed_on,
            ):
                wanted.add(current.pk)
                summary["kept"] += 1
                continue
            if current is not None:
                _revoke(current, actor, "Superseded by a revised reviewed verification link")
                summary["revoked"] += 1
            link = ProjectVerificationLink.objects.create(
                project=project,
                authority=AUTHORITY,
                registration_number=row["registration_number"],
                url=row["url"],
                basis=row["basis"],
                reviewed_on=reviewed_on,
                actor=actor,
            )
            wanted.add(link.pk)
            summary["created"] += 1
        stale = ProjectVerificationLink.objects.select_for_update().filter(active=True)
        if territory:
            stale = stale.filter(project__territory_id=territory.split(":")[0])
        for link in stale.exclude(pk__in=wanted):
            _revoke(link, actor, REVOCATION_REASON)
            summary["revoked"] += 1
    return summary


def _revoke(link, actor, reason):
    link.active = False
    link.revoked_at = timezone.now()
    link.revoked_by = actor
    link.revocation_reason = reason
    link.save(update_fields=["active", "revoked_at", "revoked_by", "revocation_reason"])
