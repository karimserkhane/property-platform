import json

from django.core.management.base import BaseCommand

from property_platform.modules.evidence.project_relations import apply_project_relations


class Command(BaseCommand):
    help = (
        "Align project component relations with the reviewed registry without collecting "
        "sources; project imports run the same step."
    )

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)
        parser.add_argument("--territory", default=None)

    def handle(self, *args, **options):
        summary = apply_project_relations(territory=options["territory"], actor=options["actor"])
        self.stdout.write(json.dumps(summary))
