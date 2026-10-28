import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from property_platform.modules.evidence.history.journals import audit_context
from property_platform.modules.evidence.history.pipeline_inventory import inventory
from property_platform.modules.evidence.models import Capture, HistoryExclusion


class Command(BaseCommand):
    help = "Inspect coverage or record/revoke an evidence-backed history exclusion."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["report", "exclude", "restore"])
        for name in ("dataset", "key", "capture", "actor", "reason"):
            parser.add_argument(f"--{name}")

    def handle(self, *args, **options):
        if options["action"] == "report":
            self.stdout.write(json.dumps(inventory(), ensure_ascii=False, indent=2))
            return
        if not all(
            options[key] and options[key].strip() for key in ("dataset", "key", "actor", "reason")
        ):
            raise CommandError("Dataset, key, actor and reason are required")
        dataset = options["dataset"]
        if dataset not in {
            f"context:{key}" for key in ("health", "schools", "mobility", "statistics", "districts")
        } and not dataset.startswith("project:"):
            raise CommandError("Only context IDs and project source URLs/claims support exclusions")
        with audit_context(actor=options["actor"]), transaction.atomic():
            if options["action"] == "restore":
                changed = HistoryExclusion.objects.filter(
                    dataset=dataset, record_key=options["key"], active=True
                ).update(
                    active=False,
                    revoked_at=timezone.now(),
                    revoked_by=options["actor"],
                    revocation_reason=options["reason"],
                )
                self.stdout.write(f"Restored exclusions: {changed}")
            else:
                if (
                    not options["capture"]
                    or not Capture.objects.filter(pk=options["capture"]).exists()
                ):
                    raise CommandError("An existing evidence capture is required")
                decision, _ = HistoryExclusion.objects.get_or_create(
                    dataset=dataset,
                    record_key=options["key"],
                    active=True,
                    defaults={
                        "capture_id": options["capture"],
                        "actor": options["actor"],
                        "reason": options["reason"],
                    },
                )
                self.stdout.write(f"Exclusion: {decision.pk}")
