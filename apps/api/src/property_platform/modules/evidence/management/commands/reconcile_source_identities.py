import json

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand, CommandError

from property_platform.modules.evidence.identity_repair import (
    repair_source_identities,
    reverse_identity_decision,
)


class Command(BaseCommand):
    help = "Review provider OBJECTID refreshes; dry-run by default, retaining all source history."

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)
        parser.add_argument("--run", help="Completed reviewed provider acquisition UUID")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--revert", action="store_true")
        parser.add_argument("--target", choices=["parcel", "administrative_area"])
        parser.add_argument("--decision", type=int)
        parser.add_argument("--reason")

    def handle(self, *args, **options):
        try:
            if options["revert"]:
                if options["run"] or options["target"] is None or options["decision"] is None:
                    raise ValueError("Reversal requires target/decision instead of a source run")
                result = reverse_identity_decision(
                    target=options["target"],
                    decision_id=options["decision"],
                    actor=options["actor"],
                    reason=options["reason"],
                    apply=options["apply"],
                )
            else:
                if (
                    not options["run"]
                    or options["target"]
                    or options["decision"]
                    or options["reason"]
                ):
                    raise ValueError(
                        "Reconciliation requires only a source run, actor and optional --apply"
                    )
                result = repair_source_identities(
                    run_id=options["run"],
                    actor=options["actor"],
                    apply=options["apply"],
                )
        except (ValueError, LookupError, ObjectDoesNotExist, ValidationError) as exc:
            raise CommandError(type(exc).__name__) from exc
        self.stdout.write(json.dumps(result))
