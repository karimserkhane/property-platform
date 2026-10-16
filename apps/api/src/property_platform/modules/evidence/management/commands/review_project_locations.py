import json

from django.core.management.base import BaseCommand, CommandError

from property_platform.modules.evidence.project_locations import withdraw_camera_positions


class Command(BaseCommand):
    help = "Withdraw obsolete map camera centres while preserving captures and audit history."

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)
        parser.add_argument("--withdraw-camera-centres", action="store_true")

    def handle(self, *args, **options):
        if not options["withdraw_camera_centres"]:
            raise CommandError("Specify --withdraw-camera-centres for this reviewed correction")
        ids = withdraw_camera_positions(actor=options["actor"])
        self.stdout.write(json.dumps({"withdrawn": len(ids), "place_ids": ids}))
