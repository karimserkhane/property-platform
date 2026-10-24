"""Developer delivery history (B03): announced dates over time against register readings.

Read-only over accepted project snapshots. Every point cites the reading it comes from.
Nothing is extrapolated: a delay is reported only as a lower bound proven by a register
reading that still shows the project unfinished after an announced period has ended.
"""

import calendar
from datetime import date

from django.db.models import Exists, OuterRef

from property_platform.modules.catalog.models import Developer, Project

from .models import HistoryExclusion
from .project_adrec import REGISTER_TIMEZONE
from .project_queries import _accepted_snapshots, _source

# Register wording that states completion. Any other status is "not completed".
COMPLETED_STATUSES = {"adrec": {"Completed"}}


def announced_window(precision, year, quarter=None, month=None, day=None):
    """First and last day an announced handover value designates, as published."""
    if precision == "year":
        return date(year, 1, 1), date(year, 12, 31)
    if precision == "quarter":
        first = 3 * quarter - 2
        return date(year, first, 1), date(year, first + 2, calendar.monthrange(year, first + 2)[1])
    if precision == "month":
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    if precision == "day":
        return date(year, month, day), date(year, month, day)
    raise ValueError(f"Unknown handover precision: {precision}")


def _change(previous, current):
    if previous is None:
        return "first"
    if current["window_start"] > previous["window_end"]:
        return "later"
    if current["window_end"] < previous["window_start"]:
        return "earlier"
    return "refined"


def announcement_points(readings):
    """Successive announced values per source, consecutive repeats collapsed.

    `readings` are dicts with `source_url`, `observed_at`, `value` (precision, year,
    quarter, month, day), `original_text` and `source`, in any order.
    """
    points, last_by_source = [], {}
    for reading in sorted(readings, key=lambda row: (row["source_url"], row["observed_at"])):
        previous = last_by_source.get(reading["source_url"])
        if previous is not None and previous["value"] == reading["value"]:
            previous["last_observed_at"] = reading["observed_at"]
            previous["readings"] += 1
            continue
        start, end = announced_window(*reading["value"])
        point = {
            "value": reading["value"],
            **dict(
                zip(("precision", "year", "quarter", "month", "day"), reading["value"], strict=True)
            ),
            "original_text": reading["original_text"],
            "window_start": start,
            "window_end": end,
            "first_observed_at": reading["observed_at"],
            "last_observed_at": reading["observed_at"],
            "readings": 1,
            "source": reading["source"],
        }
        point["change"] = _change(previous, point)
        points.append(point)
        last_by_source[reading["source_url"]] = point
    return sorted(points, key=lambda row: (row["first_observed_at"], row["source"]["url"]))


def register_points(readings):
    """Register statuses over time, consecutive identical readings collapsed.

    `readings` are dicts with `authority`, `observed_at`, `status`, `progress_percent`,
    `progress_inspected_on` and `source`.
    """
    points = []
    for reading in sorted(readings, key=lambda row: row["observed_at"]):
        key = (reading["status"], reading["progress_percent"], reading["progress_inspected_on"])
        if points and points[-1]["key"] == key:
            points[-1]["last_observed_at"] = reading["observed_at"]
            points[-1]["readings"] += 1
            continue
        points.append(
            {
                "key": key,
                "status": reading["status"],
                "completed": reading["status"]
                in COMPLETED_STATUSES.get(reading["authority"], set()),
                "progress_percent": reading["progress_percent"],
                "progress_inspected_on": reading["progress_inspected_on"],
                "first_observed_at": reading["observed_at"],
                "last_observed_at": reading["observed_at"],
                "readings": 1,
                "source": reading["source"],
            }
        )
    for point in points:
        del point["key"]
    return points


def _day(instant):
    return instant.astimezone(REGISTER_TIMEZONE).date()


def completion(points):
    """First register reading that states completion and the last one before it that did not."""
    for index, point in enumerate(points):
        if point["completed"]:
            before = next((row for row in reversed(points[:index]) if not row["completed"]), None)
            return {
                "observed_at": point["first_observed_at"],
                "source": point["source"],
                "not_completed_until": before["last_observed_at"] if before else None,
            }
    return None


def outcome(announcement, points):
    """`met`, `late` (with its proven lower bound) or `undetermined`, never a guess.

    Met: the register stated completion on or before the announced period's last day.
    Late: a reading after that day still did not state completion; the delay is at
    least the days between the period's end and the latest such reading.
    """
    end = announcement["window_end"]
    met = next(
        (row for row in points if row["completed"] and _day(row["first_observed_at"]) <= end),
        None,
    )
    if met is not None:
        return {"status": "met", "late_by_at_least_days": None, "source": met["source"]}
    late = [row for row in points if not row["completed"] and _day(row["last_observed_at"]) > end]
    if late:
        latest = max(late, key=lambda row: row["last_observed_at"])
        return {
            "status": "late",
            "late_by_at_least_days": (_day(latest["last_observed_at"]) - end).days,
            "source": latest["source"],
        }
    return {"status": "undetermined", "late_by_at_least_days": None, "source": None}


def project_history(announcements, register):
    points = register_points(register)
    announced = announcement_points(announcements)
    for point in announced:
        point["outcome"] = outcome(point, points)
    return {
        "announcements": announced,
        "register_readings": points,
        "completion": completion(points),
    }


def summarise(projects):
    def count(predicate):
        return sum(1 for project in projects if predicate(project))

    return {
        "projects": len(projects),
        "with_announcements": count(lambda row: row["announcements"]),
        "with_register": count(lambda row: row["register_readings"]),
        "completed_observed": count(lambda row: row["completion"] is not None),
        "late_observed": count(
            lambda row: any(point["outcome"]["status"] == "late" for point in row["announcements"])
        ),
        "announcement_moved_later": count(
            lambda row: any(point["change"] == "later" for point in row["announcements"])
        ),
    }


def developer_delivery_history(key):
    """Published projects of one developer with their dated, cited delivery points."""
    developer = Developer.objects.filter(key=key).first()
    if developer is None:
        return None
    accepted = _accepted_snapshots()
    projects = list(
        Project.objects.filter(developer=developer)
        .filter(Exists(accepted.filter(project_id=OuterRef("id"))))
        .order_by("name", "slug")
    )
    if not projects:
        return None
    excluded = {
        (dataset.removeprefix("project:"), record_key)
        for dataset, record_key in HistoryExclusion.objects.filter(
            dataset__in=[f"project:{project.slug}" for project in projects], active=True
        ).values_list("dataset", "record_key")
    }
    snapshots = (
        accepted.filter(project__in=projects)
        .exclude(handover_precision="", verification__isnull=True)
        .select_related("capture", "project__developer", "verification")
        .defer("capture__payload")
        .order_by("capture__fetched_at", "id")
    )
    announcements, register = {}, {}
    for snapshot in snapshots:
        slug = snapshot.project.slug
        if snapshot.handover_precision and (
            (slug, f"{snapshot.capture.url}#handover") not in excluded
        ):
            announcements.setdefault(snapshot.project_id, []).append(
                {
                    "source_url": snapshot.capture.url,
                    "observed_at": snapshot.capture.fetched_at,
                    "value": (
                        snapshot.handover_precision,
                        snapshot.handover_year,
                        snapshot.handover_quarter,
                        snapshot.handover_month,
                        snapshot.handover_day,
                    ),
                    "original_text": snapshot.handover_original,
                    "source": _source(snapshot, snapshot.handover_pointer),
                }
            )
        facts = getattr(snapshot, "verification", None)
        # A registration that only identifies a component never describes the project.
        if facts is not None and facts.fact_scope == "project" and facts.register_status:
            register.setdefault(snapshot.project_id, []).append(
                {
                    "authority": facts.authority,
                    "observed_at": snapshot.capture.fetched_at,
                    "status": facts.register_status,
                    "progress_percent": facts.progress_percent,
                    "progress_inspected_on": facts.progress_inspected_on,
                    "source": _source(snapshot, facts.evidence_pointer),
                }
            )
    rows = []
    for project in projects:
        history = project_history(announcements.get(project.id, []), register.get(project.id, []))
        rows.append(
            {"slug": project.slug, "name": project.name, "territory": project.territory_id}
            | history
        )
    return {
        "developer": {
            "id": developer.id,
            "key": developer.key,
            "name": developer.name,
            "website_url": developer.website_url,
        },
        "summary": summarise(rows),
        "projects": rows,
    }
