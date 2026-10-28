import json

from django.core.management.base import BaseCommand

from property_platform.modules.evidence.projects.project_market_labels import (
    apply_project_market_labels,
)


class Command(BaseCommand):
    help = (
        "Align project ADREC sales labels with the reviewed registry without collecting "
        "sources; project imports run the same step."
    )

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)
        parser.add_argument("--territory", default=None)

    def handle(self, *args, **options):
        summary = apply_project_market_labels(
            territory=options["territory"], actor=options["actor"]
        )
        self.stdout.write(json.dumps(summary))
