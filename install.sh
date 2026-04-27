#!/usr/bin/env bash

set -Eeuo pipefail

REPO_URL="${RAKKIB_REPO:-https://github.com/FayaaDev/Rakkib.git}"
BRANCH="${RAKKIB_BRANCH:-main}"

log()  { printf '==> %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
command_exists() { command -v "$1" >/dev/null 2>&1; }

_prompt() {
  local var_name="$1" prompt_text="$2"
  if { true < /dev/tty; } 2>/dev/null; then
    printf '%s' "$prompt_text" > /dev/tty
    IFS= read -r "$var_name" < /dev/tty
  else
    printf '%s' "$prompt_text"
    IFS= read -r "$var_name"
  fi
}

detect_platform() {
  case "$(uname -s 2>/dev/null || true)" in
    Linux|Darwin) ;;
    *) die "unsupported OS; expected Linux or macOS" ;;
  esac
}

# Pick install directory
SUDO_USER_HOME=""
if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
  SUDO_USER_HOME="$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f6 || true)"
fi

if [[ -z "${RAKKIB_DIR:-}" && -f "pyproject.toml" && -d ".git" ]]; then
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

Rakkib bootstrapper. Clones or updates the repo, creates a project-local
venv, installs the rakkib CLI into it, and links it onto PATH.

Environment overrides:
  RAKKIB_DIR       target checkout path   (default: $HOME/Rakkib)
  RAKKIB_REPO      git repo URL           (default: https://github.com/FayaaDev/Rakkib.git)
  RAKKIB_BRANCH    git branch             (default: main)
USAGE
}

parse_args() {
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --dir)    [[ "$#" -ge 2 ]] || die "missing value for --dir";    INSTALL_DIR="$2"; shift 2 ;;
      --repo)   [[ "$#" -ge 2 ]] || die "missing value for --repo";   REPO_URL="$2";    shift 2 ;;
      --branch) [[ "$#" -ge 2 ]] || die "missing value for --branch"; BRANCH="$2";      shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) die "unknown argument: $1" ;;
    esac
  done
}

confirm_root() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    local answer
    [[ -e /dev/tty ]] && printf 'WARNING: You are running Rakkib as root.\n' > /dev/tty
    _prompt answer 'Are you sure you want to continue? (y/N) ' || exit 1
    case "$answer" in y|Y) ;; *) exit 1 ;; esac
  fi
}

ensure_tooling() {
  command_exists git  || die "git is required. Install git and rerun."
  command_exists curl || warn "curl is not installed; install it before Cloudflare and download steps."
}

# Install python3 + python3-venv via the system package manager.
# Uses DPkg::Lock::Timeout so it waits for apt locks automatically.
ensure_python3_and_venv() {
  local need_python need_venv
  need_python=0; need_venv=0
  command_exists python3 || need_python=1
  python3 -c "import venv, ensurepip" 2>/dev/null || need_venv=1

  if [[ $need_python -eq 0 && $need_venv -eq 0 ]]; then
    return 0
  fi

  if command_exists apt-get; then
    local pkgs=()
    [[ $need_python -eq 1 ]] && pkgs+=(python3)
    if [[ $need_venv -eq 1 ]]; then
      local pyver
      pyver=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "")
      pkgs+=(python3-venv)
      [[ -n "$pyver" ]] && pkgs+=("python${pyver}-venv")
    fi
    log "Refreshing apt index..."
    sudo apt-get update -qq -o Acquire::Retries=3 \
      || warn "apt-get update failed; continuing with existing index."
    log "Installing ${pkgs[*]} via apt-get..."
    sudo apt-get install -y -qq --no-install-recommends -o DPkg::Lock::Timeout=60 "${pkgs[@]}" \
      || die "Failed to install ${pkgs[*]}. Run 'sudo apt-get update && sudo apt-get install --no-install-recommends ${pkgs[*]}' and rerun install.sh."
  elif command_exists dnf; then
    local pkgs=()
    [[ $need_python -eq 1 ]] && pkgs+=(python3)
    # venv ships with python3 on Fedora/RHEL
    [[ ${#pkgs[@]} -gt 0 ]] && sudo dnf install -y "${pkgs[@]}"
  elif command_exists pacman; then
    [[ $need_python -eq 1 ]] && sudo pacman -Sy --noconfirm python
  elif command_exists brew; then
    [[ $need_python -eq 1 ]] && brew install python
  else
    die "Could not find a package manager. Install python3 (with venv module) manually and rerun."
  fi

  command_exists python3 || die "python3 installation failed. Install manually and rerun."
  python3 -c "import venv, ensurepip" 2>/dev/null || die "python3-venv unavailable (including ensurepip). Install it manually and rerun."
}

is_empty_dir() {
  [[ -d "$1" ]] || return 1
  [[ -z "$(ls -A "$1" 2>/dev/null)" ]]
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
    log "Updating from origin/${BRANCH}"
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

ensure_venv_install() {
  local venv_dir="${INSTALL_DIR}/.venv"
  local bin_dir="${HOME}/.local/bin"
  local target="${bin_dir}/rakkib"

  if [[ ! -d "$venv_dir" ]]; then
    log "Creating venv at ${venv_dir}"
    python3 -m venv "$venv_dir"
  fi

  log "Installing rakkib into venv..."
  "${venv_dir}/bin/pip" install -q -e "${INSTALL_DIR}" \
    || die "pip install failed. Check the error above and rerun."

  mkdir -p "$bin_dir"
  # Overwrite symlink if it points elsewhere (e.g. stale pipx path)
  if [[ -L "$target" || ! -e "$target" ]]; then
    ln -sf "${venv_dir}/bin/rakkib" "$target"
    log "Linked ${target} -> ${venv_dir}/bin/rakkib"
  else
    warn "${target} exists and is not a symlink; skipping link creation."
  fi
}

ensure_shell_path() {
  local marker="# Added by Rakkib: user-local bin on PATH"
  local files=()
  [[ -f "${HOME}/.bashrc"  ]] && files+=("${HOME}/.bashrc")
  [[ -f "${HOME}/.zshrc"   ]] && files+=("${HOME}/.zshrc")
  [[ -f "${HOME}/.profile" ]] && files+=("${HOME}/.profile")
  [[ ${#files[@]} -eq 0 ]] && files=("${HOME}/.bashrc")

  for profile in "${files[@]}"; do
    grep -Fq "$marker" "$profile" 2>/dev/null && continue
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
  cat <<EOF

Rakkib is installed.

Repo:  ${INSTALL_DIR}
Venv:  ${INSTALL_DIR}/.venv

Next step:
  rakkib init

If rakkib is not on PATH yet, run one of:
  source ~/.bashrc   |   source ~/.zshrc   |   source ~/.profile

Or run directly:
  ${HOME}/.local/bin/rakkib init

To uninstall:
  rm -rf ${INSTALL_DIR} ${HOME}/.local/bin/rakkib

EOF
}

main() {
  parse_args "$@"
  detect_platform
  confirm_root
  ensure_tooling
  ensure_python3_and_venv
  prepare_repo
  ensure_venv_install
  ensure_shell_path
  print_next_steps
}

main "$@"
