#!/usr/bin/env bash
# CI-equivalent web checks on Linux (no Windows SWC cache issue). Runs in the checks-web
# container; CHECK_BUILD=1 also builds the standalone site and runs the HTTP smoke test.
set -euo pipefail
cd /workspace

echo "== install (Linux node_modules in volumes)"
pnpm install --frozen-lockfile --prefer-offline
echo "== lint, contracts, types, tests"
pnpm lint
pnpm contracts:check
pnpm typecheck
pnpm test:web
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  pnpm docs:check
else
  echo "docs:check skipped: git worktree metadata is outside the container; run it on the host"
fi
if [ "${CHECK_BUILD:-0}" = "1" ]; then
  echo "== build and smoke"
  pnpm build
  node scripts/prepare-web-runtime.mjs
  pnpm smoke:web
fi
