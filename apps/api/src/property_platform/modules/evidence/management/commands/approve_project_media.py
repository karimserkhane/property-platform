from django.core.management.base import BaseCommand, CommandError

from property_platform.modules.evidence.projects.project_media_storage import approve_project_media


class Command(BaseCommand):
    help = "Record an operator's review of a separate grant permitting delivery of project media."

    def add_arguments(self, parser):
        for name in (
            "media-id",
            "rights-capture-id",
            "actor",
            "author",
            "licence-code",
            "licence-url",
        ):
            parser.add_argument(f"--{name}", required=True)

    def handle(self, *args, **options):
        try:
            media = approve_project_media(
                options["media_id"],
                rights_capture_id=options["rights_capture_id"],
                actor=options["actor"],
                author=options["author"],
                licence_code=options["licence_code"],
                licence_url=options["licence_url"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(
            f"Reviewed media: {media.id}; public CDN publishing remains a separate action."
        )
