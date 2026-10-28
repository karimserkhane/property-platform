#!/usr/bin/env bash
# CI-equivalent API checks. Runs in the checks-api container (infra/local/compose.checks.yaml);
# extra arguments are passed to pytest.
set -euo pipefail
cd /workspace

echo "== ruff"
ruff check --no-cache apps/api
ruff format --check --no-cache apps/api
echo "== module boundaries"
(cd apps/api && lint-imports --config pyproject.toml --no-cache)
echo "== django"
python apps/api/manage.py check
python apps/api/manage.py makemigrations --check --dry-run
echo "== generated contracts"
contracts=$(mktemp -d)
python -m property_platform.export_openapi --output "$contracts/openapi.json"
for name in openapi.json territories.json map-credits.json; do
  if ! cmp -s "$contracts/$name" "packages/contracts/$name"; then
    echo "packages/contracts/$name is stale: regenerate it (see DEVELOPMENT.md)" >&2
    exit 1
  fi
done
echo "== tests (PostGIS)"
python -m pytest apps/api/tests -c apps/api/pyproject.toml -p no:cacheprovider -q "$@"
