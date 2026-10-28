@../AGENTS.md

## Claude Code specifics

- Talk to the owner in French; repository code, commits and engineering docs follow the existing conventions.
- Before starting, run `git status` and `git branch --show-current`. If the main checkout has uncommitted changes (usually Codex's), work in a separate worktree (`../property-platform-claude`) on a `claude/<topic>` branch instead of touching them.
- GitHub CLI is at `C:\Program Files\GitHub CLI\gh.exe` (may be missing from PATH in older shells).
- Windows host: both Git Bash and PowerShell are available. Follow `docs/engineering/DEVELOPMENT.md` for commands and `docs/engineering/TOOLCHAIN.md` for versions.
