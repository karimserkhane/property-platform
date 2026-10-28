import json

from django.core.management.base import BaseCommand, CommandError

from property_platform.modules.evidence.capture_storage import (
    DEFAULT_MIN_BYTES,
    capture_body_report,
    relocate_capture_bodies,
)


class Command(BaseCommand):
    help = (
        "report: where capture bodies live. relocate: copy SQL bodies to private storage, "
        "verify them, then clear the SQL copy (bounded batch, safe to rerun)."
    )

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["report", "relocate"])
        parser.add_argument("--actor")
        parser.add_argument("--limit", type=int, default=200)
        parser.add_argument("--min-bytes", type=int, default=DEFAULT_MIN_BYTES)

    def handle(self, *args, **options):
        try:
            if options["action"] == "report":
                result = capture_body_report(min_bytes=options["min_bytes"])
            else:
                if not options["actor"]:
                    raise CommandError("--actor is required to relocate capture bodies")
                result = relocate_capture_bodies(
                    actor=options["actor"],
                    limit=options["limit"],
                    min_bytes=options["min_bytes"],
                )
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(json.dumps(result))
