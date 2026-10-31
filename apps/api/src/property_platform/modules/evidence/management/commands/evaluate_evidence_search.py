import json

from django.core.management.base import BaseCommand

from property_platform.modules.evidence.search.evaluation import MODES, evaluate


class Command(BaseCommand):
    help = "Evaluate the evidence search on the published statements, read only."

    def add_arguments(self, parser):
        parser.add_argument("--mode", action="append", choices=MODES)
        parser.add_argument("--k", type=int, default=10)

    def handle(self, *args, mode=None, k=10, **options):
        result = evaluate(modes=tuple(mode or MODES), k=k)
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
