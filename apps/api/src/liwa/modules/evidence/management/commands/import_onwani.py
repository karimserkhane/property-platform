from django.core.management.base import BaseCommand, CommandError

from liwa.modules.evidence.services import import_onwani


class Command(BaseCommand):
    help = "Acquire Al Reem parcels directly from DMT/Onwani, with evidence and audit."

    def add_arguments(self, parser):
        parser.add_argument(
            "--actor", required=True, help="Operator identifier for the audit trail"
        )

    def handle(self, *args, **options):
        actor = options["actor"].strip()
        if not actor or len(actor) > 160:
            raise CommandError("Actor must contain 1–160 characters")
        try:
            run = import_onwani(actor=actor)
        except Exception as exc:
            raise CommandError(
                f"Import failed ({type(exc).__name__}); inspect evidence_ingestionrun. "
                "No partial catalogue acquisition is applied."
            ) from exc
        self.stdout.write(self.style.SUCCESS(f"Run {run.id}: {run.summary}"))
