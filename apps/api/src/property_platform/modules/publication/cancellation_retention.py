"""Developer retention on cancellation (B04), read from a dated, cited schedule.

Administrative Decision No. 165 of 2025 (Abu Dhabi) sets the share of the sale
contract value a developer may deduct when a defaulting purchaser's off-plan unit
is cancelled, by construction stage at cancellation. The official text has not
been obtained; the schedule below is copied from the cited commentaries, which do
not say whether 10 %, 30 % and 60 % belong to the lower or the upper band. An
exact boundary therefore returns both rates rather than a guess. This is a
reading aid that points to its sources, not legal advice.
"""

from decimal import Decimal

VERSION = "adrec-decision-165-2025-v1"

SOURCE = {
    "decision": "Administrative Decision No. 165 of 2025",
    "official_text_obtained": False,
    "references": [
        {
            "publisher": "A&O Shearman",
            "published_on": "2026-09-08",
            "url": "https://www.aoshearman.com/en/insights/abu-dhabis-new-escrow-and-off-plan-sales-regime-from-momentum-to-regulated-delivery",
            "consulted_on": "2026-10-25",
            "covers": "full schedule, stage assessed by ADREC, 60 % paid discretion",
        },
        {
            "publisher": "Trowers & Hamlins",
            "published_on": "2026-04-22",
            "url": "https://www.trowers.com/insights/2026/april/four-key-decisions-reshaping-abu-dhabi",
            "consulted_on": "2026-10-25",
            "covers": "10 % to 40 % range, full refund case, 60 % paid discretion",
        },
    ],
}

# (lower completion %, upper completion %, retention % of the sale contract value).
BANDS = (
    (Decimal(0), Decimal(10), 10),
    (Decimal(10), Decimal(30), 15),
    (Decimal(30), Decimal(60), 25),
    (Decimal(60), Decimal(100), 40),
)

# Above this share of the unit value paid by the purchaser, ADREC decides case by case.
PAID_SHARE_DISCRETION_PERCENT = 60


def retention(progress_percent):
    """Retention for a declared completion percentage; never interpolated or rounded."""
    result = {
        "version": VERSION,
        "progress_percent": progress_percent,
        "rates": [],
        "bands": [],
        # A full refund applies when works have not started for reasons outside the
        # developer's control: a cause the register percentage alone cannot show.
        "full_refund_possible": False,
        "paid_share_discretion_percent": PAID_SHARE_DISCRETION_PERCENT,
        "source": SOURCE,
    }
    if progress_percent is None:
        return {**result, "status": "unknown"}
    progress = Decimal(str(progress_percent))
    if not progress.is_finite() or progress < 0 or progress > 100:
        return {**result, "status": "out_of_range"}
    bands = [band for band in BANDS if band[0] <= progress <= band[1]]
    if progress == BANDS[0][0] or progress == BANDS[-1][1]:
        # 0 % and 100 % are the schedule's own ends, not boundaries between two bands.
        bands = bands[:1] if progress == BANDS[0][0] else bands[-1:]
    return {
        **result,
        "status": "rate" if len(bands) == 1 else "boundary",
        "rates": [band[2] for band in bands],
        "bands": [{"lower_percent": band[0], "upper_percent": band[1]} for band in bands],
        "full_refund_possible": progress == 0,
    }


def project_retention(declared_progress):
    """Retention at the latest completion the register declares, cited and dated."""
    if declared_progress is None:
        return None
    return retention(declared_progress["progress_percent"]) | {
        "progress_inspected_on": declared_progress["progress_inspected_on"],
        "progress_source": declared_progress["source"],
    }
