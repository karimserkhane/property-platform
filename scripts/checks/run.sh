#!/usr/bin/env bash
# Runs the Docker checks of this worktree without disturbing another worktree's (A39).
# From the repository or worktree root, in Git Bash (or any bash with docker and git):
#   bash scripts/checks/run.sh checks-api [command...]       # also checks-ingestion, checks-web, checks-e2e
#   bash scripts/checks/run.sh build checks-web [...]        # (re)build images of this worktree
#   bash scripts/checks/run.sh e2e-demo up -d --wait api     # demo e2e stack of this worktree
#   bash scripts/checks/run.sh e2e-demo run --rm checks-e2e
#   bash scripts/checks/run.sh e2e-demo down
# Images are tagged with the worktree's folder name and checks-web uses volumes of its own
# (infra/local/compose.checks.yaml); each checks-api run has its own test database
# (scripts/checks/api.sh). `run` always passes --no-deps: shared services are never started,
# stopped or recreated. The approved HTTPS authority of TOOLCHAIN.md is passed to image builds
# when the main checkout holds it.
set -euo pipefail
export MSYS_NO_PATHCONV=1

root=$(git rev-parse --show-toplevel)
cd "$root"
slug=$(basename "$root" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9\n' '-' | tr -s '-' | sed 's/^-//; s/-$//')
if [ -z "$slug" ]; then
  echo "Cannot derive a worktree name from $root" >&2
  exit 1
fi
export CHECKS_TAG="$slug"
export CHECKS_VOLUMES="property-platform-checks-$slug"

# The authority is an ignored file of the main checkout; worktrees share it.
main_checkout=$(cd "$(git rev-parse --git-common-dir)/.." && pwd)
for ca in "$root/.cache/validation/ingestion-trusted-ca.crt" \
  "$main_checkout/.cache/validation/ingestion-trusted-ca.crt"; do
  if [ -s "$ca" ]; then
    export PLATFORM_EXTRA_CA_FILE="$ca"
    break
  fi
done

checks=(docker compose -f infra/local/compose.yaml -f infra/local/compose.checks.yaml --profile checks)
case "${1:-}" in
  "")
    sed -n '2,8p' "$0" >&2
    exit 2
    ;;
  build)
    shift
    exec "${checks[@]}" build "$@"
    ;;
  e2e-demo)
    shift
    exec docker compose -p "property-platform-e2e-demo-$slug" -f infra/local/compose.e2e-demo.yaml "$@"
    ;;
  *)
    exec "${checks[@]}" run --rm --no-deps "$@"
    ;;
esac
