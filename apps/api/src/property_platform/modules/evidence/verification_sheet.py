"""Project verification sheet (B05): register facts, official links and contradictions.

Read-only over accepted project snapshots. Every fact cites the reading it comes from.
A contradiction only puts two cited readings side by side; it never names a cause or
picks which source is right.
"""

from .delivery_history import _day, delivery_readings, project_history
from .models import ProjectVerificationLink
from .project_queries import _source


def register_facts(snapshot):
    """What the latest project-scope register reading states, as published."""
    facts = snapshot.verification
    valid_until = facts.progress_report_valid_until
    return {
        "authority": facts.authority,
        "registration_number": facts.registration_number,
        "permit_number": facts.permit_number or None,
        "register_status": facts.register_status or None,
        "off_plan": facts.off_plan,
        "registered_on": facts.registered_on,
        "progress_percent": facts.progress_percent,
        "progress_inspected_on": facts.progress_inspected_on,
        "inspection_company": facts.inspection_company or None,
        "progress_report_url": facts.progress_report_url or None,
        "progress_report_valid_until": valid_until,
        # Judged at the reading itself, not at the visitor's date.
        "progress_report_expired": valid_until < _day(snapshot.capture.fetched_at)
        if valid_until
        else None,
        "sold_percent": facts.sold_percent,
        "sold_original": facts.sold_original or None,
        "escrow_bank_name": facts.escrow_bank_name or None,
        "escrow_account_number": facts.escrow_account_number or None,
        "developer_licence": facts.developer_licence or None,
        "observed_at": snapshot.capture.fetched_at,
        "source": _source(snapshot, facts.evidence_pointer),
    }


def _current(announcements):
    """Latest announced value of each source; earlier values are history, not claims."""
    latest = {}
    for point in sorted(announcements, key=lambda row: row["last_observed_at"]):
        latest[point["source"]["url"]] = point
    return sorted(latest.values(), key=lambda row: (row["window_start"], row["source"]["url"]))


def _contradiction(code, announcements=(), readings=(), late_by=None):
    return {
        "code": code,
        "late_by_at_least_days": late_by,
        "announcements": list(announcements),
        "register_readings": list(readings),
    }


def contradictions(history):
    """Cited disagreements between current announcements and register readings.

    - `announced_after_completion`: a source still announced, after the register first
      stated completion, a period starting later than that reading.
    - `announced_period_passed`: a source's current period has ended and a later register
      reading still did not state completion (the delay is a lower bound).
    - `sources_disagree`: two sources currently announce periods that do not overlap.
    - `progress_decreased`: a register record later declared less progress than before.
    """
    found = []
    readings = history["register_readings"]
    completed = next((row for row in readings if row["completed"]), None)
    current = _current(history["announcements"])
    for point in current:
        if (
            completed is not None
            and point["last_observed_at"] >= completed["first_observed_at"]
            and point["window_start"] > _day(completed["first_observed_at"])
        ):
            found.append(_contradiction("announced_after_completion", [point], [completed]))
        elif point["outcome"]["status"] == "late":
            proof = next(row for row in readings if row["source"] == point["outcome"]["source"])
            late_by = point["outcome"]["late_by_at_least_days"]
            found.append(_contradiction("announced_period_passed", [point], [proof], late_by))
    for index, first in enumerate(current):
        for second in current[index + 1 :]:
            if first["window_end"] < second["window_start"]:
                found.append(_contradiction("sources_disagree", [first, second]))
    by_record = {}
    for row in readings:
        by_record.setdefault(row["source"]["url"], []).append(row)
    for rows in by_record.values():
        known = [row for row in rows if row["progress_percent"] is not None]
        for earlier, later in zip(known, known[1:], strict=False):
            if later["progress_percent"] < earlier["progress_percent"]:
                found.append(_contradiction("progress_decreased", readings=[earlier, later]))
    return found


def project_verification_sheet(project, accepted):
    """Latest register facts, register history, official links and contradictions."""
    announcements, register, newest = delivery_readings(accepted, [project])
    history = project_history(announcements.get(project.id, []), register.get(project.id, []))
    latest = newest.get(project.id)
    links = ProjectVerificationLink.objects.filter(project=project, active=True).order_by(
        "authority", "registration_number"
    )
    return {
        "latest_reading": register_facts(latest) if latest else None,
        "register_readings": history["register_readings"],
        "completion": history["completion"],
        "official_links": [
            {
                "authority": link.authority,
                "registration_number": link.registration_number,
                "url": link.url,
                "reviewed_on": link.reviewed_on,
            }
            for link in links
        ],
        "contradictions": contradictions(history),
    }
