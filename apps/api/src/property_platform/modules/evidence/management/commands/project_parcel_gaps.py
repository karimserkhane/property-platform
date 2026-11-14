import json
from collections import Counter

from django.core.management.base import BaseCommand

from property_platform.modules.evidence.projects.activity_import import (
    measurement_targets,
    parcel_review_queue,
)


class Command(BaseCommand):
    help = (
        "List published projects without a parcel to measure, with the reason, "
        "ADREC off-plan sales first (B09). Read-only."
    )

    def add_arguments(self, parser):
        parser.add_argument("--territory")

    def handle(self, *args, territory=None, **options):
        rows = parcel_review_queue(territory)
        for row in rows:
            self.stdout.write(json.dumps(row, ensure_ascii=False))
        reasons = Counter(reason for row in rows for reason in row["reasons"])
        self.stderr.write(
            json.dumps(
                {
                    "measurement_targets": len(measurement_targets(territory)),
                    "projects_to_review": len(rows),
                    "adrec_off_plan": sum(row["adrec_off_plan"] for row in rows),
                    "reasons": dict(sorted(reasons.items())),
                }
            )
        )
