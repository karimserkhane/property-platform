#!/usr/bin/env bash
# CI-equivalent API checks. Runs in the checks-api container (infra/local/compose.checks.yaml);
# extra arguments are passed to pytest.
set -euo pipefail
cd /workspace

# A39: a test database of its own for this run (the container's hostname is unique), so
# checks from two worktrees never drop each other's. Django removes it at the end, also
# when tests fail; a run killed midway leaves it behind: scripts/checks/clean-test-databases.sh.
export PROPERTY_PLATFORM_TEST_DB_NAME="${PROPERTY_PLATFORM_TEST_DB_NAME:-test_property_platform_$(hostname | tr -cd 'a-z0-9' | cut -c1-24)}"
# A45: copied from template_postgis, as a role without superuser rights will need (DATABASE_ROLES.md).
export PROPERTY_PLATFORM_TEST_DB_TEMPLATE="${PROPERTY_PLATFORM_TEST_DB_TEMPLATE:-template_postgis}"
echo "== test database: $PROPERTY_PLATFORM_TEST_DB_NAME (from $PROPERTY_PLATFORM_TEST_DB_TEMPLATE)"

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
