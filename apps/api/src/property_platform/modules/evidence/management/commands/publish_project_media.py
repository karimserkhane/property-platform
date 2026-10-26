from django.core.management.base import BaseCommand, CommandError

from property_platform.modules.evidence.projects.project_media_storage import publish_project_media


class Command(BaseCommand):
    help = "Publish one explicitly approved project file to the separate configured CDN bucket."

    def add_arguments(self, parser):
        parser.add_argument("--media-id", required=True)
        parser.add_argument("--actor", required=True)

    def handle(self, *args, **options):
        try:
            publication = publish_project_media(options["media_id"], actor=options["actor"])
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(f"Published media: {publication.media_id}")
