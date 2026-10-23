#!/usr/bin/env bash
# CI-equivalent ingestion checks. Runs in the checks-ingestion container; extra arguments
# are passed to pytest.
set -euo pipefail
cd /workspace

echo "== ruff"
ruff check --no-cache apps/ingestion
ruff format --check --no-cache apps/ingestion
echo "== tests"
python -m pytest apps/ingestion/tests -c apps/ingestion/pyproject.toml -p no:cacheprovider -q "$@"
