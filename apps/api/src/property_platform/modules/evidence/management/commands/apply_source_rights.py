import json

from django.core.management.base import BaseCommand

from property_platform.modules.evidence.history.journals import audit_context
from property_platform.modules.evidence.source_rights_import import apply_source_rights


class Command(BaseCommand):
    help = (
        "Mirror the reviewed source rights registry into evidence.source_rights; the "
        "source-rights flow and rebuilds run the same step."
    )

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)

    def handle(self, *args, **options):
        with audit_context(actor=options["actor"]):
            summary = apply_source_rights(actor=options["actor"])
        self.stdout.write(json.dumps(summary))
