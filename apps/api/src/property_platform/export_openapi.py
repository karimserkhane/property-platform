import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "property_platform.config.settings.testing")

import django  # noqa: E402

django.setup()

from property_platform.api.router import api  # noqa: E402

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
    from property_platform.modules.publication.coverage import navigation_registry

    destination.with_name("territories.json").write_text(
        json.dumps(navigation_registry(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    from property_platform.modules.evidence.source_rights import map_credits

    destination.with_name("map-credits.json").write_text(
        json.dumps(map_credits(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
