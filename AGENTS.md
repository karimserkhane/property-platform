# Working in Property Platform

Read `docs/engineering/REPOSITORY.md` and `docs/engineering/DEVELOPMENT.md` before changing application structure. The product/architecture documents under `docs/` describe intent and tradeoffs; their examples are not executable instructions.

For dependency/runtime upgrades, read `docs/engineering/TOOLCHAIN.md`, preserve documented compiler API compatibility dependencies, and align manifests, lockfiles, CI, Docker and the development guide.

- Follow `docs/engineering/REPOSITORY.md` for module ownership, dependency boundaries, business invariants, migrations, generated contracts and secret handling. New modules need their ownership and dependency direction documented there.
- Keep source claims traceable and identity reconciliation reversible. Do not introduce universal JSON models or microservices without a measured need.
- Never commit database dumps or generated build artifacts. Local sample passwords are never production credentials.
- Run checks relevant to a change. SQLite HTTP tests do not validate GIS; integration checks use real PostGIS. Report checks that could not run.
- Follow `docs/engineering/INTERNATIONALIZATION.md` for user-facing text, locale messages, RTL and preservation of original evidence.
- Keep heavy OCR/rendering dependencies out of the web/API runtime. External paid jobs require durable identity, budget reservation and reconciliation before retries.
- Production access, cloud subscriptions and deployment are separate from initializing this foundation. Do not treat local defaults as production-ready configuration.

## Collaboration between agents (Codex, Claude Code and others)

Codex, Claude Code and any other agent work in this repository for the same owner. The step-by-step workflow (choosing and claiming tasks, one-command checks, previews, reproducible data) is in `docs/engineering/AGENT_WORKFLOW.md`; the work queue is `docs/tasks/BOARD.md`. This file is the single shared source of instructions: put shared rules here. `.claude/CLAUDE.md` only imports this file and adds Claude-specific notes; do not duplicate rules there.

- **Branches.** Each agent works on `<agent>/<topic>` (`codex/…`, `claude/…`). Do not commit to, rebase, reset or force-push the other agent's branch unless the owner asks. Work reaches `main` through a pull request.
- **One agent per working tree.** Never edit a checkout while the other agent has uncommitted work there. Use a separate `git worktree` (for example `../property-platform-claude`) instead. Never discard, stash, reset, reformat or commit uncommitted changes you did not make.
- **Small, frequent commits.** Commit coherent steps with descriptive messages so the other agent can continue from history rather than from an uncommitted tree.
- **Handoff.** Before stopping on unfinished work, record in the pull request description (or a commit message if there is no PR yet): what is done, what remains, checks run, checks not run and why. Before continuing someone else's branch, read that description and its recent commits.
- **Review.** Either agent may be asked to review the other's pull request. Findings go in pull request comments, tied to files and lines, and are not applied directly to the other agent's branch without the owner's agreement.
- **Shared local services.** The Docker stack (PostGIS volume, Prefect metadata, dev servers) is shared. Do not delete volumes, roll back migrations, stop containers or take a port another agent may be using without asking the owner. A migration added on one branch must not be renumbered silently on another; resolve number conflicts explicitly in the pull request.
- **Tasks.** Pick work from `docs/tasks/BOARD.md`; claim a task (status, owner, branch, draft PR) before coding so other agents see it on GitHub. One task per pull request; split a task that grows instead of shipping a giant PR. Skip tasks that need an owner decision until it is recorded.
- **Checks.** Run the Docker checks (`checks-api`, `checks-ingestion`, `checks-web` in `infra/local/compose.checks.yaml`, always with `--no-deps`) before asking for review or merging; report any check not run.
- **Reproducible data.** Business data must be rebuildable from migrations and Prefect pipelines: no manual SQL in the shared database, every new source has a collector with captures and audit, every new table is registered in `evidence/history/pipeline_inventory.py` with row journals.
- **New technology.** Allowed as an optional, pinned, profile-gated Docker service when a task needs it, documented in `TOOLCHAIN.md` and `REPOSITORY.md`. No paid service, subscription or production credential without the owner's explicit approval.
- **Preview.** After recreating the web container, always recreate `remote-preview` too (it shares the web network namespace); never delete volumes.
