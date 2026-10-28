import json
from pathlib import Path

from django.core.management.base import BaseCommand

from property_platform.modules.evidence.rebuild.demo_package import export_package


class Command(BaseCommand):
    help = (
        "Export the reviewed acquisitions of a demonstration package (selection.json) "
        "from this database, read-only, with provenance per capture (A13)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--package", required=True, type=Path)

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(export_package(options["package"])))
