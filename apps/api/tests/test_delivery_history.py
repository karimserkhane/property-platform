"""Delivery history rules (B03): no extrapolation, every point cites its reading."""

from datetime import UTC, date, datetime

import pytest

from property_platform.modules.evidence.projects.delivery_history import (
    announced_window,
    project_history,
    summarise,
)


def source(url, day):
    return {"url": url, "retrieved_at": day}


def announcement(url, day, value, text):
    observed = datetime(*day, 8, tzinfo=UTC)
    return {
        "source_url": url,
        "observed_at": observed,
        "value": value,
        "original_text": text,
        "source": source(url, observed),
    }


def register(day, status, progress=None, hour=8):
    observed = datetime(*day, hour, tzinfo=UTC)
    return {
        "authority": "adrec",
        "observed_at": observed,
        "status": status,
        "progress_percent": progress,
        "progress_inspected_on": None,
        "source": source(
            "https://adrec.gov.ae/api/feature/Profession/ProjectDetail?id=1", observed
        ),
    }


DEVELOPER = "https://developer.example/project"
BROKER = "https://broker.example/project"


@pytest.mark.parametrize(
    ("value", "window"),
    [
        (("year", 2026, None, None, None), (date(2026, 1, 1), date(2026, 12, 31))),
        (("quarter", 2028, 1, None, None), (date(2028, 1, 1), date(2028, 3, 31))),
        (("quarter", 2027, 4, None, None), (date(2027, 10, 1), date(2027, 12, 31))),
        (("month", 2028, None, 2, None), (date(2028, 2, 1), date(2028, 2, 29))),
        (("day", 2027, None, 6, 30), (date(2027, 6, 30), date(2027, 6, 30))),
    ],
)
def test_an_announced_value_designates_its_published_period_only(value, window):
    assert announced_window(*value) == window


def test_successive_announcements_are_kept_per_source_and_compared_within_it():
    history = project_history(
        [
            announcement(DEVELOPER, (2025, 1, 5), ("year", 2026, None, None, None), "2026"),
            announcement(DEVELOPER, (2025, 3, 5), ("year", 2026, None, None, None), "2026"),
            announcement(DEVELOPER, (2025, 6, 5), ("quarter", 2026, 4, None, None), "Q4 2026"),
            announcement(DEVELOPER, (2025, 9, 5), ("quarter", 2027, 2, None, None), "Q2 2027"),
            # Another source disagreeing is not a postponement by the developer.
            announcement(BROKER, (2025, 2, 1), ("quarter", 2028, 1, None, None), "Q1 2028"),
        ],
        [],
    )
    points = history["announcements"]
    assert [(row["original_text"], row["change"]) for row in points] == [
        ("2026", "first"),
        ("Q1 2028", "first"),
        ("Q4 2026", "refined"),
        ("Q2 2027", "later"),
    ]
    first = points[0]
    assert first["readings"] == 2
    assert first["last_observed_at"] == datetime(2025, 3, 5, 8, tzinfo=UTC)
    assert first["source"]["url"] == DEVELOPER
    assert all(row["outcome"]["status"] == "undetermined" for row in points)
    assert history["completion"] is None


def test_lateness_is_only_the_lower_bound_a_register_reading_proves():
    history = project_history(
        [announcement(DEVELOPER, (2025, 1, 5), ("quarter", 2025, 2, None, None), "Q2 2025")],
        [
            register((2025, 6, 1), "Under Construction", 80),
            register((2025, 9, 15), "Under Construction", 95),
            register((2025, 9, 20), "Under Construction", 95),
            register((2025, 12, 1), "Completed", 100),
        ],
    )
    outcome = history["announcements"][0]["outcome"]
    # Still unfinished on 20 September, 82 days after 30 June; the true delay is unknown.
    assert outcome == {
        "status": "late",
        "late_by_at_least_days": 82,
        "source": history["register_readings"][1]["source"],
    }
    assert [row["readings"] for row in history["register_readings"]] == [1, 2, 1]
    assert history["completion"]["observed_at"] == datetime(2025, 12, 1, 8, tzinfo=UTC)
    assert history["completion"]["not_completed_until"] == datetime(2025, 9, 20, 8, tzinfo=UTC)


def test_completion_by_the_announced_day_is_met_and_unseen_periods_stay_undetermined():
    met = project_history(
        [announcement(DEVELOPER, (2025, 1, 5), ("year", 2025, None, None, None), "2025")],
        [register((2025, 4, 1), "Under Construction", 60), register((2025, 11, 1), "Completed")],
    )
    assert met["announcements"][0]["outcome"]["status"] == "met"
    # Completion first seen after the period, never seen unfinished after it: unknown.
    unseen = project_history(
        [announcement(DEVELOPER, (2025, 1, 5), ("quarter", 2025, 1, None, None), "Q1 2025")],
        [register((2025, 2, 1), "Under Construction", 60), register((2025, 5, 1), "Completed")],
    )
    assert unseen["announcements"][0]["outcome"]["status"] == "undetermined"


def test_the_register_day_is_read_in_uae_time():
    # 21:00 UTC on 30 June is already 1 July in Abu Dhabi, after the announced day.
    history = project_history(
        [announcement(DEVELOPER, (2025, 1, 5), ("day", 2025, None, 6, 30), "30 June 2025")],
        [register((2025, 6, 30), "Under Construction", 99, hour=21)],
    )
    assert history["announcements"][0]["outcome"]["late_by_at_least_days"] == 1


def test_summary_counts_observations_without_rates():
    late = {
        "announcements": [{"change": "later", "outcome": {"status": "late"}}],
        "register_readings": [{}],
        "completion": None,
    }
    quiet = {"announcements": [], "register_readings": [], "completion": None}
    assert summarise([late, quiet]) == {
        "projects": 2,
        "with_announcements": 1,
        "with_register": 1,
        "completed_observed": 0,
        "late_observed": 1,
        "announcement_moved_later": 1,
    }
