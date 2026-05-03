# Plan: Slim `runtime` branch for the curl installer (bead Rakkib-pgs)

## Context

Today the curl-pipe installer fetches `install.sh` from `main`, then `install.sh` clones the entire `main` branch into the target host. That drags dev-only files onto every server: `.beads/`, `.beads.zip`, `.claude/`, `.opencode/`, `docs/`, `services/`, `tests/`, `web/`, `AGENTS.md`, `CLAUDE.md`, `WebUI.md`, `pyqr.md`. None of those are needed for `rakkib` to run — install.sh only needs `pyproject.toml` + `src/rakkib/**` (the package + its bundled `data/` templates).

The fix: create a dedicated `runtime` branch that holds only the runtime-required files, and update `install.sh` to default to that branch. The public curl-pipe command stays identical:

```
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash
```

`install.sh` lives on `main` (so `raw.githubusercontent.com/.../main/install.sh` keeps working), but its default `BRANCH` becomes `runtime`, so the clone it performs lands a slim tree on the host.

## Confirmed facts (from exploration)

- `install.sh:5-6` — `REPO_URL` and `BRANCH` are env-overridable (`RAKKIB_REPO`, `RAKKIB_BRANCH`); `--repo`/`--branch` flags exist (`install.sh:63-73`).
- `install.sh:211` — clone is `git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"` (full clone, no shallow/single-branch flags).
- `install.sh:234` — `pip install -e "${INSTALL_DIR}"` requires `pyproject.toml` + `src/rakkib/` at the repo root. Nothing else.
- `pyproject.toml:21-25` — package discovered via `where = ["src"]`; `package-data` includes `data/**/*`. So everything under `src/rakkib/data/` ships in the install.
- `src/rakkib/**` does not reach outside the package. All template/registry lookups resolve via `Path(__file__).resolve().parent / "data"` (e.g., `src/rakkib/steps/__init__.py:60`, `schema.py:12`, `steps/services.py:51`).
- `cli.py:533` sets `repo_dir = Path(__file__).resolve().parent` — the editable install makes this `<INSTALL_DIR>/src/rakkib`. State file `.fss-state.yaml` is gitignored.
- `.gitignore` is load-bearing for re-runs: `install.sh:184` does `git status --porcelain` to decide whether to auto-update; without `.gitignore`, the host's `.venv/` shows as untracked and every re-run skips updates.

## Files to keep on the `runtime` branch

Required (load-bearing):

- `install.sh` — so re-runs from inside the checkout still work, and `--branch` flag is discoverable.
- `pyproject.toml` — needed by `pip install -e`.
- `.gitignore` — keeps `.venv/`, `.fss-state.yaml`, `__pycache__/`, `*.egg-info/`, `.DS_Store` ignored on the host so `git status --porcelain` stays clean across re-runs.
- `src/rakkib/**` — entire package, including `src/rakkib/data/**` (registry.yaml, questions, templates, files).

Also included:

- A short `README.md` (5-10 lines) explaining "this is the install snapshot; develop on `main`."

Excluded (dev-only):

- `.beads/`, `.beads.zip`, `.claude/`, `.opencode/`, `docs/`, `services/`, `tests/`, `web/`, `AGENTS.md`, `CLAUDE.md`, `WebUI.md`, `pyqr.md`, `.DS_Store`.

## Changes to make

### 1. Edit `install.sh` on `main`

Two edits, both mechanical:

- `install.sh:6` — change `BRANCH="${RAKKIB_BRANCH:-main}"` → `BRANCH="${RAKKIB_BRANCH:-runtime}"`.
- `install.sh:59` — update the `usage()` text: `RAKKIB_BRANCH    git branch             (default: runtime)`.
- `install.sh:211` — change clone to shallow single-branch:
  `git clone --depth 1 --single-branch --no-tags --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"`.

Rationale for `--depth 1 --single-branch --no-tags`: smallest possible install; the bead asks for it; `git pull --ff-only` at line 201 still works on a depth-1 clone.

### 2. Create the `runtime` orphan branch

Use a **`git worktree` with an orphan branch** so the main checkout is left completely untouched (the working tree currently has `.beads.zip` and other untracked files we must not disturb). The orphan branch starts with no history, so the resulting clone is minimal and no dev files are reachable through history.

Steps (run after step 1 has been committed to `main`):

```bash
# from /Users/fayaa/projy/Rakkib (on main, install.sh edits already committed)
git worktree add --orphan -b runtime ../rakkib-runtime
cd ../rakkib-runtime

# Materialize only runtime files from main
git checkout main -- install.sh pyproject.toml .gitignore src/

# Write the slim runtime README
cat > README.md <<'EOF'
# Rakkib — runtime branch

This branch is the slim install snapshot used by the curl-pipe installer.
It contains only the files needed to run `rakkib` on a target host:
`install.sh`, `pyproject.toml`, `.gitignore`, `src/rakkib/**`.

For development, issues, docs, and tests, see the `main` branch:
https://github.com/FayaaDev/Rakkib/tree/main

To sync this branch from `main` after changes land there:
    git fetch origin
    git switch runtime
    git checkout main -- install.sh pyproject.toml .gitignore src/
    git commit -m "sync from main@<sha>"
    git push
EOF

git add install.sh pyproject.toml .gitignore src/ README.md
git commit -m "runtime: initial slim snapshot from main"
git push -u origin runtime

cd -
git worktree remove ../rakkib-runtime
```

### 3. Order of operations

1. Edit + commit + push `install.sh` on `main` (step 1 above).
2. Create `runtime` from the updated `main` (step 2 above) — `git checkout main -- install.sh` then pulls in the new defaults, so `install.sh` is byte-identical on both branches.

### 4. Future sync workflow (out of scope, but flag in commit message)

When `src/rakkib/**`, `pyproject.toml`, or `install.sh` change on `main`, someone needs to mirror the change to `runtime`. Simplest manual recipe (document in the runtime branch's README):

```bash
git fetch origin
git switch runtime
git checkout main -- install.sh pyproject.toml .gitignore src/
git commit -m "sync from main@<sha>"
git push
```

Automating this (CI workflow that pushes to `runtime` whenever those paths change on `main`) is a follow-up bead.

## Critical files to modify / touch

- `/Users/fayaa/projy/Rakkib/install.sh` — lines 6, 59, 211.
- New orphan branch `runtime` containing: `install.sh`, `pyproject.toml`, `.gitignore`, `src/rakkib/**`, slim `README.md`.

No Python source changes. No `pyproject.toml` changes. No template changes.

## Verification

End-to-end check:

1. **Lint the runtime tree.** After pushing `runtime`:
   ```bash
   git ls-tree -r runtime --name-only | sort
   ```
   Confirm output contains exactly: `install.sh`, `pyproject.toml`, `.gitignore`, `README.md`, and `src/rakkib/**`. Confirm absence of: `.beads/`, `.claude/`, `.opencode/`, `docs/`, `services/`, `tests/`, `web/`, `AGENTS.md`, `CLAUDE.md`, `WebUI.md`, `pyqr.md`.

2. **Local clone smoke test (no install).**
   ```bash
   git clone --depth 1 --single-branch --no-tags --branch runtime \
     https://github.com/FayaaDev/Rakkib.git /tmp/rakkib-runtime-test
   ls /tmp/rakkib-runtime-test                # should be ~5 entries
   ls /tmp/rakkib-runtime-test/src/rakkib/data  # should show registry.yaml, templates/, questions/, files/
   rm -rf /tmp/rakkib-runtime-test
   ```

3. **Bare-metal install (per CLAUDE.md rules — must run on a fresh server, NOT this dev machine).** On a fresh Ubuntu 24.04 box:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash
   ls ~/Rakkib                                # confirm slim tree
   ~/.local/bin/rakkib --version              # confirm CLI runs
   ```

4. **Override still works.** On the same fresh box (separate dir):
   ```bash
   RAKKIB_BRANCH=main RAKKIB_DIR=~/Rakkib-dev \
     bash <(curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh)
   ```
   Confirm `~/Rakkib-dev` contains the full `main` tree (with `tests/`, `docs/`, etc.).

5. **Re-run idempotency.** Re-execute the curl-pipe install on the bare-metal box; confirm `install.sh` reports "Updating from origin/runtime" and exits cleanly.

## Risks

- **`install.sh` drift between branches.** If someone edits `install.sh` only on `main`, hosts on `runtime` re-running `bash install.sh` from inside the checkout will use the older copy. Mitigation: future sync workflow includes `install.sh`.
- **Existing hosts pinned to `main`.** Already-installed hosts have `BRANCH=main` baked into their checkout (and re-runs use `RAKKIB_BRANCH` from env, defaulting to whatever's in the new install.sh). They will auto-switch to `runtime` on next re-run because install.sh:188-202 does `git switch "$BRANCH"` if the working tree is clean. That is the intended migration path; no manual host intervention needed.
- **`--depth 1` on first install + later branch switch.** If a user later sets `RAKKIB_BRANCH=main` on an existing depth-1 `runtime` checkout, the `git fetch origin main` at line 195 will fetch only that ref's tip; switch should still succeed. Acceptable.
