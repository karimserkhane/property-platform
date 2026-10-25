"""Verification sheet contradictions (B05): cited readings side by side, no inference."""

from test_delivery_history import BROKER, DEVELOPER, announcement, register

from property_platform.modules.evidence.delivery_history import project_history
from property_platform.modules.evidence.verification_sheet import contradictions

Q1_2026 = ("quarter", 2026, 1, None, None)
Q4_2027 = ("quarter", 2027, 4, None, None)
Y2028 = ("year", 2028, None, None, None)


def codes(announcements, readings):
    return [row["code"] for row in contradictions(project_history(announcements, readings))]


def test_consistent_readings_raise_nothing():
    assert codes([announcement(DEVELOPER, (2026, 1, 5), Q4_2027, "Q4 2027")], []) == []
    assert (
        codes(
            [announcement(DEVELOPER, (2026, 1, 5), Q4_2027, "Q4 2027")],
            [register((2026, 2, 1), "Under Construction", 40)],
        )
        == []
    )


def test_an_announcement_kept_after_register_completion_is_a_contradiction():
    found = contradictions(
        project_history(
            [announcement(DEVELOPER, (2026, 3, 1), Y2028, "Handover 2028")],
            [register((2026, 2, 1), "Completed", 100)],
        )
    )
    (row,) = found
    assert row["code"] == "announced_after_completion"
    assert row["announcements"][0]["source"]["url"] == DEVELOPER
    assert row["register_readings"][0]["completed"] is True


def test_an_announcement_seen_only_before_completion_is_history():
    assert (
        codes(
            [announcement(DEVELOPER, (2026, 1, 1), Y2028, "Handover 2028")],
            [register((2026, 2, 1), "Completed", 100)],
        )
        == []
    )


def test_a_passed_period_cites_the_unfinished_reading_and_a_lower_bound():
    (row,) = contradictions(
        project_history(
            [announcement(DEVELOPER, (2025, 6, 1), Q1_2026, "Q1 2026")],
            [register((2026, 4, 10), "Under Construction", 80)],
        )
    )
    assert row["code"] == "announced_period_passed"
    assert row["late_by_at_least_days"] == 10
    assert row["register_readings"][0]["status"] == "Under Construction"


def test_only_the_current_value_of_a_source_is_compared():
    # The developer moved its date; the earlier, passed period is history only.
    assert (
        codes(
            [
                announcement(DEVELOPER, (2025, 6, 1), Q1_2026, "Q1 2026"),
                announcement(DEVELOPER, (2026, 3, 1), Q4_2027, "Q4 2027"),
            ],
            [register((2026, 4, 10), "Under Construction", 80)],
        )
        == []
    )


def test_sources_announcing_periods_that_do_not_overlap_disagree():
    (row,) = contradictions(
        project_history(
            [
                announcement(BROKER, (2026, 1, 5), Y2028, "2028"),
                announcement(DEVELOPER, (2026, 1, 5), Q4_2027, "Q4 2027"),
            ],
            [],
        )
    )
    assert row["code"] == "sources_disagree"
    assert [item["source"]["url"] for item in row["announcements"]] == [DEVELOPER, BROKER]
    assert (
        codes(
            [
                announcement(BROKER, (2026, 1, 5), ("year", 2027, None, None, None), "2027"),
                announcement(DEVELOPER, (2026, 1, 5), Q4_2027, "Q4 2027"),
            ],
            [],
        )
        == []
    )


def test_lower_progress_in_a_later_reading_is_shown_with_both_readings():
    (row,) = contradictions(
        project_history(
            [],
            [
                register((2026, 1, 1), "Under Construction", 45),
                register((2026, 2, 1), "Under Construction", 30),
                register((2026, 3, 1), "Under Construction", None),
            ],
        )
    )
    assert row["code"] == "progress_decreased"
    assert [item["progress_percent"] for item in row["register_readings"]] == [45, 30]
