# Rakkib — Agent Rules

## This project boots new servers

Assume the target machine is **bare metal** — only `curl`, `git`, and `python3` may be present. The `install.sh` script is the sole entry point. It must bring up everything else (venv, pip, rakkib CLI) without pre-existing tooling.

Dont debug and run tests on current machine, the app is being tested on a bare metal machine. Not this one

Solo one-line command:
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash

## Guidelines

- **`install.sh` is sacred.** Any change must pass on a fresh Ubuntu 24.04 server. Test by running `bash install.sh` in a clean checkout.
- **Assume nothing about the host.** No `python3-venv`, no `pip`, no `ensurepip`. The `ensure_python3_and_venv()` function handles all of this — keep it bulletproof.
- **Check both `venv` and `ensurepip`.** The venv module can import while `ensurepip` is broken. Always check `import venv, ensurepip` when validating the Python toolchain.
- **No fancy shell constructs.** The script runs under `set -Eeuo pipefail`. Keep it POSIX-compatible (no arrays in `/bin/sh`, though `bash` features are fine since shebang is `#!/usr/bin/env bash`).
- **Error messages must be actionable.** Every `die()` call should tell the user exactly what command to run to fix it.
- **The venv lives at `<repo>/.venv`**, not system-wide.
- **The rakkib symlink goes to `~/.local/bin/rakkib`**, and `ensure_shell_path()` adds that to PATH in `~/.bashrc`, `~/.zshrc`, and `~/.profile`.
- **curl-pipe safety:** The script is designed to be piped from `curl ... | bash`. Never add prompts that require `/dev/tty` when stdin is a pipe.
