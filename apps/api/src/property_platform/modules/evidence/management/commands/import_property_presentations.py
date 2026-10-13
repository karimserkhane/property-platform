import json
from pathlib import Path

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from property_platform.modules.evidence.collection_profiles import COLLECTIONS
from property_platform.modules.evidence.property_import import import_presentations, registry


class Command(BaseCommand):
    help = (
        "Import reviewed property presentations and licensed images "
        "from verified acquisition receipts."
    )

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)
        parser.add_argument("--territory", choices=tuple(COLLECTIONS), default="al-reem-island")
        parser.add_argument("--receipt", required=True, type=Path)

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("Property presentation import requires PostGIS")
        try:
            if options["receipt"].stat().st_size > 32 * 1024 * 1024:
                raise ValueError("Property receipt file exceeds budget")
            profiles, photos = registry(options["territory"])
            records = import_presentations(
                json.loads(options["receipt"].read_text(encoding="utf-8-sig")),
                actor=options["actor"],
                profiles=profiles,
                photos=photos,
            )
        except (ValueError, KeyError, OSError, ObjectDoesNotExist) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            f"Imported {len(records)} property presentations; catalogue identities preserved."
        )
