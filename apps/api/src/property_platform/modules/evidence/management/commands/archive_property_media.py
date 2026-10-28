import json

from django.core.management.base import BaseCommand, CommandError

from property_platform.modules.evidence.media_storage import archive_property_media


class Command(BaseCommand):
    help = "Archive approved photos; --publish explicitly copies them to the configured CDN bucket."

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)
        parser.add_argument("--limit", type=int, default=500)
        parser.add_argument("--publish", action="store_true")

    def handle(self, *args, **options):
        try:
            result = archive_property_media(
                actor=options["actor"], limit=options["limit"], publish=options["publish"]
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(json.dumps(result))
