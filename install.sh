#!/usr/bin/env bash

set -Eeuo pipefail

REPO_URL="${RAKKIB_REPO:-https://github.com/FayaaDev/Rakkib.git}"
BRANCH="${RAKKIB_BRANCH:-main}"
BOOTSTRAP_URL="${RAKKIB_BOOTSTRAP_URL:-https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh}"

if [[ -f "AGENT_PROTOCOL.md" && -f "lib/common.sh" ]]; then
  # shellcheck source=lib/common.sh
  . "lib/common.sh"
else
  log() { printf '==> %s\n' "$*"; }
  warn() { printf 'WARNING: %s\n' "$*" >&2; }
  die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
  command_exists() { command -v "$1" >/dev/null 2>&1; }
  detect_platform() {
    case "$(uname -s 2>/dev/null || true)" in
      Linux|Darwin) ;;
      *) die "unsupported OS; expected Linux or Mac" ;;
    esac
  }
fi

SUDO_USER_HOME=""
if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
  SUDO_USER_HOME="$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f6 || true)"
fi

if [[ -z "${RAKKIB_DIR:-}" && -f "AGENT_PROTOCOL.md" && -d ".git" ]]; then
  INSTALL_DIR="$(pwd)"
elif [[ -n "${RAKKIB_DIR:-}" ]]; then
  INSTALL_DIR="${RAKKIB_DIR}"
elif [[ "${EUID:-$(id -u)}" -eq 0 && -n "$SUDO_USER_HOME" ]]; then
  INSTALL_DIR="${SUDO_USER_HOME}/Rakkib"
elif [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  INSTALL_DIR="/opt/rakkib"
else
  INSTALL_DIR="${HOME}/Rakkib"
fi

usage() {
  cat <<'USAGE'
Usage: install.sh [--dir <path>] [--repo <url>] [--branch <name>]

Rakkib bootstrapper. It clones or updates the installer repo, ensures python3
and pipx are present, pipx-installs the Rakkib CLI, adds ~/.local/bin to
shell profiles when needed, and prints the next command to run.

Environment overrides:
  RAKKIB_DIR       target checkout path, default: $HOME/Rakkib
  RAKKIB_REPO      git repo URL, default: https://github.com/FayaaDev/Rakkib.git
  RAKKIB_BRANCH    git branch, default: main
USAGE
}

parse_args() {
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --dir)
        [[ "$#" -ge 2 ]] || die "missing value for --dir"
        INSTALL_DIR="$2"
        shift 2
        ;;
      --repo)
        [[ "$#" -ge 2 ]] || die "missing value for --repo"
        REPO_URL="$2"
        shift 2
        ;;
      --branch)
        [[ "$#" -ge 2 ]] || die "missing value for --branch"
        BRANCH="$2"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "unknown argument: $1"
        ;;
    esac
  done
}

confirm_root() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    local answer
    printf 'WARNING: You are running Rakkib as root.\n' > /dev/tty
    printf 'Are you sure you want to continue y/N ' > /dev/tty
    IFS= read -r answer < /dev/tty || exit 1
    case "$answer" in
      y|Y) ;;
      *) exit 1 ;;
    esac
  fi
}

ensure_python3() {
  command_exists python3 || die "python3 is required. Install python3, then rerun this bootstrapper."
}

ensure_pipx() {
  if command_exists pipx; then
    return 0
  fi
  log "pipx not found. Installing pipx..."
  if command_exists pip3; then
    pip3 install --user pipx >/dev/null 2>&1 || true
  fi
  if ! command_exists pipx && command_exists python3; then
    python3 -m pip install --user pipx >/dev/null 2>&1 || true
  fi
  if command_exists pipx; then
    return 0
  fi
  if [[ -x "${HOME}/.local/bin/pipx" ]]; then
    export PATH="${HOME}/.local/bin:${PATH}"
  fi
  command_exists pipx || die "pipx installation failed. Install pipx manually (https://pypa.github.io/pipx/) and rerun."
}

pipx_install_repo() {
  if [[ ! -f "${INSTALL_DIR}/pyproject.toml" ]]; then
    warn "No pyproject.toml found in ${INSTALL_DIR}; falling back to symlink shim."
    return 1
  fi
  log "Installing Rakkib via pipx from ${INSTALL_DIR}"
  pipx install --force "$INSTALL_DIR" >/dev/null 2>&1 || {
    warn "pipx install failed; falling back to symlink shim."
    return 1
  }
  log "Installed rakkib CLI via pipx"
}

ensure_tooling() {
  command_exists git || die "git is required. Install git, then rerun this bootstrapper."
  command_exists curl || warn "curl is not installed; install it before Cloudflare and download-heavy steps."
}

is_empty_dir() {
  local dir="$1"
  [[ -d "$dir" ]] || return 1
  [[ -z "$(ls -A "$dir" 2>/dev/null)" ]]
}

repo_has_local_changes() {
  [[ -n "$(git -C "$INSTALL_DIR" status --porcelain 2>/dev/null)" ]]
}

prepare_repo() {
  if [[ -d "${INSTALL_DIR}/.git" ]]; then
    log "Using existing checkout: ${INSTALL_DIR}"
    if repo_has_local_changes; then
      warn "Existing checkout has local changes; skipping automatic update."
      return 0
    fi

    log "Updating existing checkout from origin/${BRANCH}"
    git -C "$INSTALL_DIR" fetch origin "$BRANCH"
    if git -C "$INSTALL_DIR" show-ref --verify --quiet "refs/heads/${BRANCH}"; then
      git -C "$INSTALL_DIR" switch "$BRANCH"
    else
      git -C "$INSTALL_DIR" switch -c "$BRANCH" "origin/${BRANCH}"
    fi
    git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
    return 0
  fi

  if [[ -e "$INSTALL_DIR" ]] && ! is_empty_dir "$INSTALL_DIR"; then
    die "target path exists and is not an empty git checkout: ${INSTALL_DIR}"
  fi

  mkdir -p "$(dirname "$INSTALL_DIR")"
  log "Cloning ${REPO_URL} into ${INSTALL_DIR}"
  git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
}

install_cli_shim() {
  local target="${HOME}/.local/bin/rakkib"
  if [[ -e "$target" && ! -L "$target" ]]; then
    warn "Skipping rakkib PATH shim because ${target} already exists and is not a symlink."
    return 0
  fi

  mkdir -p "${HOME}/.local/bin"
  ln -sfn "${INSTALL_DIR}/bin/rakkib" "$target"
  log "Installed rakkib CLI shim at ${target}"
}

ensure_shell_path() {
  local marker="# Added by Rakkib: user-local bin on PATH"
  local files=()

  [[ -f "${HOME}/.bashrc" ]] && files+=("${HOME}/.bashrc")
  [[ -f "${HOME}/.zshrc" ]] && files+=("${HOME}/.zshrc")
  [[ -f "${HOME}/.profile" ]] && files+=("${HOME}/.profile")

  if [[ ${#files[@]} -eq 0 ]]; then
    files=("${HOME}/.bashrc")
  fi

  for profile in "${files[@]}"; do
    if [[ -f "$profile" ]] && grep -Fq "$marker" "$profile" 2>/dev/null; then
      continue
    fi
    touch "$profile"
    {
      printf '\n%s\n' "$marker"
      printf '%s\n' 'case ":$PATH:" in'
      printf '%s\n' '  *":$HOME/.local/bin:"*) ;;'
      printf '%s\n' '  *) export PATH="$HOME/.local/bin:$PATH" ;;'
      printf '%s\n' 'esac'
    } >> "$profile"
    log "Added ~/.local/bin to PATH in ${profile}"
  done
}

print_next_steps() {
  [[ -x "${INSTALL_DIR}/bin/rakkib" ]] || warn "rakkib bash CLI is missing or not executable: ${INSTALL_DIR}/bin/rakkib"

  cat <<EOF

Rakkib is installed.

Repo:
  ${INSTALL_DIR}

Next step:
  rakkib init

If rakkib is not on PATH yet, run one of:
  source ~/.bashrc
  source ~/.zshrc
  source ~/.profile

Or run it directly:
  ${HOME}/.local/bin/rakkib init

EOF
}

main() {
  parse_args "$@"
  detect_platform
  confirm_root
  ensure_tooling
  ensure_python3
  ensure_pipx
  prepare_repo
  if ! pipx_install_repo; then
    install_cli_shim
  fi
  ensure_shell_path
  print_next_steps
}

main "$@"
