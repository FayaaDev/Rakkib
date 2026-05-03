# Rakkib — Agent Rules

## This project boots new servers

Assume the target machine is **bare metal** — only `curl`, `git`, and `python3` may be present. The `install.sh` script is the sole entry point. It must bring up everything else (venv, pip, rakkib CLI) without pre-existing tooling.

Dont debug and run tests on current machine, the app is being tested on a bare metal machine. Not this one

Solo one-line command:
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash

## Runtime branch

- `main` is the development branch and still hosts the public `install.sh` used by the curl-pipe command.
- `runtime` is an orphan branch used as the slim install snapshot. It intentionally has no shared history with `main` and should contain only `.gitignore`, `README.md`, `install.sh`, `pyproject.toml`, and `src/rakkib/**`.
- The installer defaults `RAKKIB_BRANCH` to `runtime`, so the public curl command fetches `install.sh` from `main` but clones the slim `runtime` tree onto target hosts.
- When `install.sh`, `pyproject.toml`, or `src/rakkib/**` changes on `main`, mirror those runtime files to the orphan `runtime` branch and push it. Do not copy dev-only files such as `.beads/`, `.opencode/`, `docs/`, `services/`, `tests/`, or `web/`.
- Use `RAKKIB_BRANCH=main` only when intentionally installing the full development tree.

## Guidelines

- **`install.sh` is sacred.** Any change must pass on a fresh Ubuntu 24.04 server. Test by running `bash install.sh` in a clean checkout.
- **Assume nothing about the host.** No `python3-venv`, no `pip`, no `ensurepip`. The `ensure_python3_and_venv()` function handles all of this — keep it bulletproof.
- **Check both `venv` and `ensurepip`.** The venv module can import while `ensurepip` is broken. Always check `import venv, ensurepip` when validating the Python toolchain.
- **No fancy shell constructs.** The script runs under `set -Eeuo pipefail`. Keep it POSIX-compatible (no arrays in `/bin/sh`, though `bash` features are fine since shebang is `#!/usr/bin/env bash`).
- **Error messages must be actionable.** Every `die()` call should tell the user exactly what command to run to fix it.
- **The venv lives at `<repo>/.venv`**, not system-wide.
- **The rakkib symlink goes to `~/.local/bin/rakkib`**, and `ensure_shell_path()` adds that to PATH in `~/.bashrc`, `~/.zshrc`, and `~/.profile`.
- **curl-pipe safety:** The script is designed to be piped from `curl ... | bash`. Never add prompts that require `/dev/tty` when stdin is a pipe.

## Service Additions

- **Service additions are registry-driven.** Prefer declarative changes in `src/rakkib/data/registry.yaml`, templates under `src/rakkib/data/templates/`, and hook wiring in `src/rakkib/hooks/services.py`.
- **Do not add new hardcoded `if svc_id == ...` branches** in Python unless the behavior genuinely cannot be expressed through registry fields, templates, or hooks.
- **`rakkib add` is part of the contract.** It now opens a registry-driven checkbox TUI that lists all services from `src/rakkib/data/registry.yaml`, marks already-installed services with `[X]`, and syncs the server to match the final selection.
- **Unchecked services are fully removed.** The `rakkib add` sync flow is destructive for deselected services: it tears down containers, removes rendered config, removes service data directories, deletes related generated artifacts, and drops service-specific Postgres databases/roles when declared in the registry.
- **New services must work with both `pull` and `rakkib add`.** A service is not complete unless it can be selected in the `rakkib add` TUI, deployed through that flow, and cleanly removed again through deselection.
- **Use the project-local skill** `.opencode/skills/rakkib-add-service/SKILL.md` when adding a new service so registry fields, templates, hooks, and verification updates are handled consistently.
- **Keep verification aligned with the registry architecture.** At minimum, make sure any new registry references resolve cleanly and update snapshot or fixture expectations when rendered outputs change materially.
