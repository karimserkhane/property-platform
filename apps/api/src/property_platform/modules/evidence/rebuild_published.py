"""Published state compared by the rebuild check, keyed by durable identities (A12).

Owner decision of 2026-10-24: a rebuild from the archived source bytes must reproduce
what the site publishes. History rows of earlier interpretations are an alert; their
exact rows are kept by the A03 backups. Database UUIDs, private storage locations and
ingestion clocks differ by construction and are not compared. Nothing expected is
ever written to the rebuilt database.
"""

import json
from datetime import date, datetime
from uuid import UUID

from django.db import connection

VERSION = 1
MAX_DIFFERENCES = 20
MAX_ITEMS = 5
MAX_TEXT = 300
# One row per reading of a capture. The replay reads every archived capture once, with
# the current extractor and registry: identical recollections and readings by earlier
# versions are not all recreated. A missing published fact still fails the check.
HISTORY_TABLES = {
    "evidence.project_snapshot": "Project page readings; published dossiers are compared",
    "evidence.project_typology": "Typologies per reading; published dossiers are compared",
    "evidence.project_amenity": "Amenities per reading; published dossiers are compared",
    "evidence.project_media": "Media references per reading; published dossiers are compared",
    "evidence.project_source_candidate": "Catalogue readings; a review queue, not published",
    "evidence.project_identity_link": "Revocations are operator decisions (A03); "
    "active links are compared",
}
# Database identities and this execution's clock, never source facts.
VOLATILE = frozenset({"id", "ingested_at"})
# Published fields an operator decision kept only by A03 can change; None means any.
DECISION_FIELDS = {
    "history_exclusion": None,
    "link_revocation": {"map_locations"},
    "media_publication": {"media"},
}
# A revocation withdraws a position: a rebuild may show it again, never lose or change one.
ONLY_ADDED = frozenset({"link_revocation"})


def _dump(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _short(value):
    text = _dump(value)
    return text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1] + "…"


def canonical(value, ordered=False):
    """Published items as order-independent lists; a geometry keeps its coordinate order."""
    if isinstance(value, dict):
        result = {}
        for key, item in sorted(value.items()):
            if key in VOLATILE:
                continue
            if key == "delivery_url":
                # A private storage location per database; being delivered is the fact.
                result["delivered"] = item is not None
            else:
                result[key] = canonical(item, ordered or key == "geometry")
        return result
    if isinstance(value, list | tuple):
        items = [canonical(item, ordered) for item in value]
        return items if ordered else sorted(items, key=_dump)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, UUID):
        # Not a durable identity: kept so that it fails the comparison, never trusted.
        return str(value)
    return value


def identity_links():
    """Active reviewed project-to-map links by provider identity."""
    from .models import ProjectIdentityLink

    rows = []
    for link in ProjectIdentityLink.objects.filter(active=True).select_related(
        "project", "building", "place", "parcel"
    ):
        target = "building" if link.building_id else "place" if link.place_id else "parcel"
        record = getattr(link, target)
        rows.append(
            {
                "project": link.project.slug,
                "target": target,
                "namespace": record.source_namespace,
                "record_id": record.source_record_id,
                "reason": link.reason,
            }
        )
    return sorted(rows, key=_dump)


def operator_decisions():
    """Projects whose publication depends on decisions only the A03 backups restore."""
    from django.db.models import Q

    from .models import HistoryExclusion, ProjectIdentityLink, ProjectMedia

    result = {}
    for dataset in HistoryExclusion.objects.filter(
        active=True, dataset__startswith="project:"
    ).values_list("dataset", flat=True):
        result.setdefault(dataset.split(":", 1)[1], set()).add("history_exclusion")
    for slug in ProjectMedia.objects.filter(
        Q(rights_status="approved") | Q(projectmediapublication__isnull=False)
    ).values_list("snapshot__project__slug", flat=True):
        result.setdefault(slug, set()).add("media_publication")
    for slug in ProjectIdentityLink.objects.filter(active=False).values_list(
        "project__slug", flat=True
    ):
        result.setdefault(slug, set()).add("link_revocation")
    return {slug: sorted(kinds) for slug, kinds in sorted(result.items())}


def published_state():
    """Canonical dossiers of every published project and the active identity links."""
    from .project_queries import project_detail, published_slugs

    return {
        "version": VERSION,
        "projects": {slug: canonical(project_detail(slug)) for slug in published_slugs()},
        "identity_links": identity_links(),
        "decisions": operator_decisions(),
    }


def interpretations():
    """Readings per extractor version and catalogue readings: explains the history alert."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT s.extractor_version, count(*), "
            "count(DISTINCT (c.url, c.content_sha256, c.fetched_at)) "
            "FROM evidence.project_snapshot s JOIN evidence.capture c ON c.id = s.capture_id "
            "GROUP BY 1 ORDER BY 1"
        )
        readings = {
            version: {"readings": total, "receipts": receipts}
            for version, total, receipts in cursor.fetchall()
        }
        cursor.execute(
            "SELECT count(*), count(DISTINCT (publisher_key, territory_scope, source_url_sha256)) "
            "FROM evidence.project_source_candidate"
        )
        total, distinct = cursor.fetchone()
    return {
        "readings_by_extractor": readings,
        "catalogue_candidates": {"readings": total, "distinct": distinct},
    }


def differences(expected, actual, path=""):
    """Paths whose published value differs; list items missing or added by value."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        result = []
        for key in sorted(set(expected) | set(actual)):
            result += differences(expected.get(key), actual.get(key), f"{path}.{key}")
        return result
    if expected == actual:
        return []
    if isinstance(expected, list) and isinstance(actual, list):
        added = list(actual)
        missing = []
        for item in expected:
            if item in added:
                added.remove(item)
            else:
                missing.append(item)
        return [
            {
                "path": path,
                "missing": [_short(item) for item in missing[:MAX_ITEMS]],
                "added": [_short(item) for item in added[:MAX_ITEMS]],
                "counts": {"missing": len(missing), "added": len(added)},
            }
        ]
    return [{"path": path, "expected": _short(expected), "actual": _short(actual)}]


def _covered(kinds, item):
    """Decision kinds that can explain this published difference."""
    path = item["path"]
    field = path.split(".")[1] if path.startswith(".") else ""
    return sorted(
        kind
        for kind in kinds
        if ((fields := DECISION_FIELDS.get(kind, set())) is None or field in fields)
        and (kind not in ONLY_ADDED or item.get("counts", {}).get("missing", 1) == 0)
    )


def compare_published(expected, actual):
    """Blocking differences, and those only an operator decision kept by A03 explains."""
    decisions = expected.get("decisions", {})
    projects, blocking, identical = [], 0, 0
    for slug in sorted(set(expected["projects"]) | set(actual["projects"])):
        before, after = expected["projects"].get(slug), actual["projects"].get(slug)
        if before == after:
            identical += 1
            continue
        kinds = decisions.get(slug, [])
        if before is None or after is None:
            found = [{"path": "", "status": "missing" if after is None else "unexpected"}]
        else:
            found = differences(before, after)
        for item in found:
            # A whole missing or unexpected dossier is explained only by a withdrawal.
            item["requires_backup"] = _covered(kinds, item)
            blocking += not item["requires_backup"]
        projects.append(
            {
                "slug": slug,
                "differences": found[:MAX_DIFFERENCES],
                "difference_count": len(found),
                "blocking": sum(not item["requires_backup"] for item in found),
            }
        )
    links = {"expected": len(expected["identity_links"]), "actual": len(actual["identity_links"])}
    for name, rows, others, explaining in (
        ("missing", expected["identity_links"], actual["identity_links"], {"history_exclusion"}),
        (
            "added",
            actual["identity_links"],
            expected["identity_links"],
            {"history_exclusion", "link_revocation"},
        ),
    ):
        known = {_dump(row) for row in others}
        changed = [row for row in rows if _dump(row) not in known]
        unexplained = [
            row for row in changed if not explaining & set(decisions.get(row["project"], []))
        ]
        blocking += len(unexplained)
        links[name] = [_short(row) for row in changed[:MAX_DIFFERENCES]]
        links[f"{name}_blocking"] = len(unexplained)
    return {
        "version": VERSION,
        "projects": len(expected["projects"]),
        "rebuilt_projects": len(actual["projects"]),
        "identical_projects": identical,
        "different_projects": projects,
        "identity_links": links,
        "blocking": blocking,
        "requires_backup": sorted(
            project["slug"]
            for project in projects
            if project["difference_count"] and not project["blocking"]
        ),
        "ok": blocking == 0,
    }
