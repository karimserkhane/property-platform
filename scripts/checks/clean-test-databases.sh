#!/usr/bin/env bash
# Lists the per-run test databases left on the shared server by interrupted checks-api runs
# (A39, scripts/checks/api.sh), and drops them with --drop. Only names matching
# test_property_platform_<id> with no open connection are considered: never the service
# database, nor rebuild_check_* or restore_check_* (REBUILD.md, BACKUPS.md).
#   bash scripts/checks/clean-test-databases.sh          # list
#   bash scripts/checks/clean-test-databases.sh --drop   # drop the listed ones
set -euo pipefail
export MSYS_NO_PATHCONV=1
db_container="${DB_CONTAINER:-property-platform-local-db-1}"
psql=(docker exec "$db_container" psql -U property_platform -d postgres -v ON_ERROR_STOP=1 -tA)

leftovers=$("${psql[@]}" -c "
  SELECT d.datname FROM pg_database d
  WHERE d.datname ~ '^test_property_platform_[a-z0-9]{1,40}$'
    AND NOT EXISTS (SELECT 1 FROM pg_stat_activity a WHERE a.datname = d.datname)
  ORDER BY 1")

if [ -z "$leftovers" ]; then
  echo "No leftover per-run test database."
  exit 0
fi
echo "Leftover per-run test databases (no open connection):"
printf '  %s\n' $leftovers
if [ "${1:-}" != "--drop" ]; then
  echo "Run again with --drop to remove them."
  exit 0
fi
for name in $leftovers; do
  case "$name" in
    test_property_platform_*) "${psql[@]}" -c "DROP DATABASE \"$name\"" >/dev/null && echo "dropped $name" ;;
  esac
done
