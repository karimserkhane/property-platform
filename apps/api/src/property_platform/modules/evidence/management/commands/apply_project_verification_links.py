import json

from django.core.management.base import BaseCommand

from property_platform.modules.evidence.project_verification_links import (
    apply_project_verification_links,
)


class Command(BaseCommand):
    help = (
        "Align project verification page links with the reviewed registry without reading "
        "the pages; project imports run the same step."
    )

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)
        parser.add_argument("--territory", default=None)

    def handle(self, *args, **options):
        summary = apply_project_verification_links(
            territory=options["territory"], actor=options["actor"]
        )
        self.stdout.write(json.dumps(summary))
