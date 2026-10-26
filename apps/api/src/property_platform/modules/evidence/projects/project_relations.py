"""Make active project relations follow the reviewed registry; history is revoked, not lost."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from property_platform.modules.catalog.models import Project

from ..models import Capture
from ..project_models import ProjectRelation
from .project_protocol import project_relations

REVOCATION_REASON = "Removed from the reviewed project relation registry"
# Reviews are dated in the territories' local time (UAE).
REVIEW_TIMEZONE = ZoneInfo("Asia/Dubai")


def reviewed_capture(url, reviewed_on):
    """The latest successful capture of the cited page by the end of its review day.

    It does not depend on when or in which order captures were imported, so a rebuild
    from the archives cites the same evidence as the original database (A12).
    """
    until = datetime.combine(
        date.fromisoformat(reviewed_on) + timedelta(days=1), time.min, tzinfo=REVIEW_TIMEZONE
    )
    return (
        Capture.objects.filter(url=url, http_status=200, fetched_at__lt=until)
        .defer("payload")
        .order_by("-fetched_at", "-id")
        .first()
    )


def same_receipt(capture_id, capture):
    """Readings of one acquisition have distinct capture rows but the same receipt."""
    return Capture.objects.filter(
        pk=capture_id,
        url=capture.url,
        fetched_at=capture.fetched_at,
        content_sha256=capture.content_sha256,
    ).exists()


def apply_project_relations(*, territory=None, actor):
    """Create, keep or revoke relations for one territory (or all), idempotently.

    A relation waits until both projects exist and its cited source has a capture; the
    catalogue pipelines create both, so a rebuild from archives restores every link.
    """
    actor = actor.strip()
    if not 1 <= len(actor) <= 160:
        raise ValueError("Valid project relation actor required")
    rows = project_relations(territory)
    projects = {
        project.slug: project
        for project in Project.objects.filter(
            slug__in={slug for row in rows for slug in (row["child"], row["parent"])}
        )
    }
    summary = {"created": 0, "kept": 0, "revoked": 0, "waiting": 0}
    with transaction.atomic():
        wanted = set()
        for row in rows:
            child, parent = projects.get(row["child"]), projects.get(row["parent"])
            capture = reviewed_capture(row["source_url"], row["reviewed_on"])
            if child is None or parent is None or capture is None:
                summary["waiting"] += 1
                continue
            wanted.add(child.pk)
            current = (
                ProjectRelation.objects.select_for_update().filter(child=child, active=True).first()
            )
            if (
                current is not None
                and current.parent_id == parent.pk
                and (current.kind, current.component, current.basis)
                == (row["kind"], row["component"], row["basis"])
            ):
                if not same_receipt(current.capture_id, capture):
                    # Same reviewed relation: an archived capture of the review window
                    # imported later refines its citation. The row journal keeps the old one.
                    current.capture = capture
                    current.save(update_fields=["capture"])
                summary["kept"] += 1
                continue
            if current is not None:
                _revoke(current, actor, "Superseded by a revised reviewed relation")
                summary["revoked"] += 1
            ProjectRelation.objects.create(
                child=child,
                parent=parent,
                kind=row["kind"],
                component=row["component"],
                capture=capture,
                basis=row["basis"],
                reviewed_on=date.fromisoformat(row["reviewed_on"]),
                actor=actor,
            )
            summary["created"] += 1
        stale = ProjectRelation.objects.select_for_update().filter(active=True)
        if territory:
            stale = stale.filter(child__territory_id=territory.split(":")[0])
        for relation in stale.exclude(child_id__in=wanted).exclude(
            child__slug__in={row["child"] for row in rows}
        ):
            _revoke(relation, actor, REVOCATION_REASON)
            summary["revoked"] += 1
    return summary


def _revoke(relation, actor, reason):
    relation.active = False
    relation.revoked_at = timezone.now()
    relation.revoked_by = actor
    relation.revocation_reason = reason
    relation.save(update_fields=["active", "revoked_at", "revoked_by", "revocation_reason"])
