import hashlib
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from property_platform.modules.evidence.collection_profiles import COLLECTIONS, collection_for
from property_platform.modules.evidence.models import ResearchReference
from property_platform.modules.evidence.sources.research_import import (
    REGISTRY,
    import_reference,
    reprocess_reference,
)


class Command(BaseCommand):
    help = (
        "Re-read curated public project and research URLs; "
        "never copy assertions from the reference HTML."
    )

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)
        parser.add_argument("--territory", choices=tuple(COLLECTIONS), default="al-reem-island")
        parser.add_argument("--limit", type=int, default=200)
        parser.add_argument(
            "--reprocess",
            action="store_true",
            help="Reprocess stored source captures; preserve original acquisition dates",
        )

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("Reference acquisition requires the PostGIS environment")
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(716548220)")
            if not cursor.fetchone()[0]:
                raise CommandError("Map/reference acquisition already running")
        try:
            self.collect(*args, **options)
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(716548220)")

    def collect(self, *args, **options):
        if not 1 <= len(options["actor"].strip()) <= 160 or not 1 <= options["limit"] <= 200:
            raise CommandError("Valid actor and limit required")
        profile = collection_for(options["territory"])
        rows = json.loads(
            REGISTRY.with_name(profile.reference_registry).read_text(encoding="utf-8")
        )
        if options["reprocess"]:
            source_keys = [
                "research:" + hashlib.sha256(row["url"].encode()).hexdigest()[:40] for row in rows
            ]
            references = list(
                ResearchReference.objects.filter(capture__run__source__key__in=source_keys)
                .select_related("capture__run__source")
                .order_by("capture__run__source_id", "-capture__fetched_at", "-id")
                .distinct("capture__run__source_id")[: options["limit"]]
            )
            for reference in references:
                run = reprocess_reference(
                    reference, actor=options["actor"].strip(), territory=options["territory"]
                )
                self.stdout.write(f"{reference.label}: {run.status} {run.summary}")
            return
        for row in rows[: options["limit"]]:
            run = import_reference(
                row, actor=options["actor"].strip(), territory=options["territory"]
            )
            self.stdout.write(f"{row['label']}: {run.status} {run.summary}")
