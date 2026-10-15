from django.core.management.base import BaseCommand, CommandError

from property_platform.modules.evidence.project_media_storage import attach_project_media_file


class Command(BaseCommand):
    help = (
        "Archive an explicitly supplied project file privately; this does not approve publication."
    )

    def add_arguments(self, parser):
        parser.add_argument("--media-id", required=True)
        parser.add_argument("--file", required=True)
        parser.add_argument("--actor", required=True)

    def handle(self, *args, **options):
        try:
            capture = attach_project_media_file(
                options["media_id"], options["file"], actor=options["actor"]
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(f"Private capture: {capture.id}; delivery still requires rights review.")
