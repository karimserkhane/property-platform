import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "liwa.config.settings.testing")

import django  # noqa: E402

django.setup()

from liwa.api.router import api  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export the API contract to an explicit destination."
    )
    parser.add_argument("--output", type=Path, required=True)
    destination = parser.parse_args().output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(api.get_openapi_schema(path_prefix="/api/v1/"), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
