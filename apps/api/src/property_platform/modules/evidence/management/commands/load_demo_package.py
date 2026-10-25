import json
from pathlib import Path

from django.core.management.base import BaseCommand

from property_platform.modules.evidence.demo_package import load_package


class Command(BaseCommand):
    help = (
        "Replay a demonstration package into an empty, disposable database with the "
        "current importers (A13); refuses a database that already holds captures."
    )

    def add_arguments(self, parser):
        parser.add_argument("--package", required=True, type=Path)
        parser.add_argument("--actor", required=True)

    def handle(self, *args, **options):
        summary = load_package(options["package"], options["actor"])
        self.stdout.write(json.dumps(summary))
