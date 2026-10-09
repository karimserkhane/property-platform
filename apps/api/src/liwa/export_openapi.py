import json
import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "liwa.config.settings.testing")

import django  # noqa: E402

django.setup()

from liwa.api.router import api  # noqa: E402

if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[4] / "packages/contracts/openapi.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(api.get_openapi_schema(path_prefix="/api/v1/"), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
