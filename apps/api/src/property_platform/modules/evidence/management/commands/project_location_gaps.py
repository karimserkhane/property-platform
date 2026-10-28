import json

from django.core.management.base import BaseCommand

from property_platform.modules.evidence.projects.project_queries import project_location_gaps


class Command(BaseCommand):
    help = "List published projects without a documented map position, by review priority."

    def add_arguments(self, parser):
        parser.add_argument("--territory")

    def handle(self, *args, territory=None, **options):
        for row in project_location_gaps(territory):
            self.stdout.write(json.dumps(row, ensure_ascii=False))
