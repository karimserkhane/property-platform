import json
from pathlib import Path

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from property_platform.modules.evidence.property_import import import_presentations


class Command(BaseCommand):
    help = (
        "Import reviewed property presentations and licensed images "
        "from verified acquisition receipts."
    )

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)
        parser.add_argument("--receipt", required=True, type=Path)

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("Property presentation import requires PostGIS")
        try:
            if options["receipt"].stat().st_size > 32 * 1024 * 1024:
                raise ValueError("Property receipt file exceeds budget")
            records = import_presentations(
                json.loads(options["receipt"].read_text(encoding="utf-8-sig")),
                actor=options["actor"],
            )
        except (ValueError, KeyError, OSError, ObjectDoesNotExist) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            f"Imported {len(records)} property presentations; catalogue identities preserved."
        )
