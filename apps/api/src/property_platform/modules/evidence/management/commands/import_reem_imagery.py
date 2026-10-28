import json
import struct
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from property_platform.modules.evidence.sources.imagery_import import (
    BASE,
    BBOX,
    SCENES,
    import_imagery,
    validate,
)

# Compatibility for existing operator tools and integration fixtures.
__all__ = ["BASE", "BBOX", "SCENES", "validate"]


class Command(BaseCommand):
    help = "Import bounded Sentinel previews produced by the isolated imagery worker."

    def add_arguments(self, parser):
        parser.add_argument("--actor", required=True)
        parser.add_argument("--receipt", required=True)

    def handle(self, *args, **options):
        path = Path(options["receipt"])
        try:
            if path.stat().st_size > 16 * 1024 * 1024:
                raise ValueError("Receipt exceeds budget")
            rows = json.loads(path.read_text(encoding="utf-8"))
            runs = import_imagery(rows, actor=options["actor"])
        except (ValueError, KeyError, TypeError, struct.error, OSError) as exc:
            raise CommandError("Invalid imagery receipt") from exc
        for run in runs:
            self.stdout.write(
                f"{run.summary['scene']}: {'created' if run.summary['created'] else 'unchanged'}"
            )
