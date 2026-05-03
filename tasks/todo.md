# Install Shim Runtime Branch

- [x] Update `install.sh` to default clones to `runtime` and use a shallow single-branch clone.
- [x] Create an orphan `runtime` worktree containing only runtime files.
- [x] Verify the runtime branch file list excludes dev-only files.
- [x] Record verification results and any follow-up notes.

## Review

- `main` contains installer commit `a420f12` with the runtime default and shallow clone flags.
- `runtime` contains orphan root commit `c517f3c` with only `.gitignore`, `README.md`, `install.sh`, `pyproject.toml`, and `src/rakkib/**`.
- Verified `git ls-tree -r origin/runtime --name-only | sort` shows only runtime files.
- Verified dev-only paths are absent from `origin/runtime`.
- Verified a depth-1 single-branch clone of `runtime` from GitHub produces the slim tree and includes `src/rakkib/data/{files,questions,registry.yaml,templates}`.
- Did not run the bare-metal installer locally because project rules require that validation on a fresh Ubuntu 24.04 host, not this machine.
