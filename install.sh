#!/usr/bin/env bash

set -Eeuo pipefail

REPO_URL="${RAKKIB_REPO:-https://github.com/FayaaDev/Rakkib.git}"
BRANCH="${RAKKIB_BRANCH:-main}"
BOOTSTRAP_URL="${RAKKIB_BOOTSTRAP_URL:-https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh}"

# Distribution channel decision (Rakkib-94m):
# v2.0 ships via GitHub release wheel. Users will run:
#   pipx install https://github.com/FayaaDev/Rakkib/releases/download/v2.0.0/rakkib-2.0.0-py3-none-any.whl
# PyPI publication is deferred to v2.1+ for cleaner long-term discoverability.
# Until the release workflow is wired, this bootstrapper still clones the repo
# and pipx-installs from the local checkout.

log() { printf '==> %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
command_exists() { command -v "$1" >/dev/null 2>&1; }

# Read a line from /dev/tty if available, otherwise stdin.
# This lets tests pipe answers without needing a TTY.
_prompt() {
  local var_name="$1"
  local prompt_text="$2"
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
    *) die "unsupported OS; expected Linux or Mac" ;;
  esac
}

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
    if [[ -e /dev/tty ]]; then
      printf 'WARNING: You are running Rakkib as root.\n' > /dev/tty
    fi
    _prompt answer 'Are you sure you want to continue y/N ' || exit 1
    case "$answer" in
      y|Y) ;;
      *) exit 1 ;;
    esac
  fi
}

_detect_package_manager() {
  if command_exists apt-get; then
    echo "apt-get"
  elif command_exists dnf; then
    echo "dnf"
  elif command_exists yum; then
    echo "yum"
  elif command_exists pacman; then
    echo "pacman"
  elif command_exists brew; then
    echo "brew"
  elif command_exists apk; then
    echo "apk"
  else
    echo ""
  fi
}

_install_system_python_deps() {
  local pkg_mgr
  pkg_mgr="$(_detect_package_manager)"
  if [[ -z "$pkg_mgr" ]]; then
    return 1
  fi

  local packages=""
  case "$pkg_mgr" in
    apt-get)
      packages="python3-pip python3-venv"
      ;;
    dnf|yum)
      packages="python3-pip"
      ;;
    pacman)
      packages="python-pip"
      ;;
    brew)
      packages="pipx"
      ;;
    apk)
      packages="py3-pip"
      ;;
  esac

  if [[ -z "$packages" ]]; then
    return 1
  fi

  log "pipx could not be installed. The following system packages may be required: ${packages}."
  local answer
  _prompt answer "Install them via ${pkg_mgr}? (y/N) " || return 1
  case "$answer" in
    y|Y) ;;
    *) return 1 ;;
  esac

  case "$pkg_mgr" in
    apt-get)
      sudo apt-get update -qq >/dev/null 2>&1 || true
      sudo apt-get install -y -qq $packages >/dev/null 2>&1 || return 1
      ;;
    dnf)
      sudo dnf install -y $packages >/dev/null 2>&1 || return 1
      ;;
    yum)
      sudo yum install -y $packages >/dev/null 2>&1 || return 1
      ;;
    pacman)
      sudo pacman -Sy --noconfirm $packages >/dev/null 2>&1 || return 1
      ;;
    brew)
      brew install $packages >/dev/null 2>&1 || return 1
      ;;
    apk)
      sudo apk add $packages >/dev/null 2>&1 || return 1
      ;;
  esac
  return 0
}

ensure_python3() {
  if command_exists python3; then
    return 0
  fi

  log "python3 not found."
  local pkg_mgr
  pkg_mgr="$(_detect_package_manager)"
  if [[ -z "$pkg_mgr" ]]; then
    die "python3 is required. Install python3, then rerun this bootstrapper."
  fi

  local packages="python3"
  [[ "$pkg_mgr" == "brew" ]] && packages="python"

  local answer
  _prompt answer "Install ${packages} via ${pkg_mgr}? (y/N) " || die "python3 is required. Install python3, then rerun this bootstrapper."
  case "$answer" in
    y|Y) ;;
    *) die "python3 is required. Install python3, then rerun this bootstrapper." ;;
  esac

  case "$pkg_mgr" in
    apt-get)
      sudo apt-get update -qq >/dev/null 2>&1 || true
      sudo apt-get install -y -qq $packages >/dev/null 2>&1 || die "Failed to install python3 via apt-get."
      ;;
    dnf)
      sudo dnf install -y $packages >/dev/null 2>&1 || die "Failed to install python3 via dnf."
      ;;
    yum)
      sudo yum install -y $packages >/dev/null 2>&1 || die "Failed to install python3 via yum."
      ;;
    pacman)
      sudo pacman -Sy --noconfirm $packages >/dev/null 2>&1 || die "Failed to install python3 via pacman."
      ;;
    brew)
      brew install $packages >/dev/null 2>&1 || die "Failed to install python via brew."
      ;;
    apk)
      sudo apk add $packages >/dev/null 2>&1 || die "Failed to install python3 via apk."
      ;;
  esac

  command_exists python3 || die "python3 installation failed. Install python3 manually and rerun."
}

ensure_pipx() {
  if command_exists pipx; then
    return 0
  fi
  log "pipx not found. Installing pipx..."

  # 1. Try apt (preferred for PEP 668 distros like Ubuntu 23.04+)
  if _command_exists apt-get; then
    if sudo apt-get update -qq >/dev/null 2>&1 && \
       sudo apt-get install -y -qq pipx >/dev/null 2>&1; then
      pipx ensurepath >/dev/null 2>&1 || true
      command_exists pipx && return 0
    fi
  fi

  # 2. Try dnf
  if _command_exists dnf; then
    if sudo dnf install -y pipx >/dev/null 2>&1; then
      pipx ensurepath >/dev/null 2>&1 || true
      command_exists pipx && return 0
    fi
  fi

  # 3. Fallback: pip install --user (for non-PEP 668 or when apt/dnf fail)
  if command_exists pip3; then
    pip3 install --user --yes pipx >/dev/null 2>&1 || true
  fi
  if ! command_exists pipx && command_exists python3; then
    python3 -m pip install --user --yes pipx >/dev/null 2>&1 || true
  fi

  # 4. Check if pipx is now available
  if command_exists pipx; then
    python3 -m pipx ensurepath >/dev/null 2>&1 || true
    return 0
  fi
  if [[ -x "${HOME}/.local/bin/pipx" ]]; then
    export PATH="${HOME}/.local/bin:${PATH}"
    python3 -m pipx ensurepath >/dev/null 2>&1 || true
    return 0
  fi

  command_exists pipx || die "pipx installation failed. Install pipx manually (https://pypa.github.io/pipx/) and rerun."
}

pipx_install_repo() {
  if [[ ! -f "${INSTALL_DIR}/pyproject.toml" ]]; then
    warn "No pyproject.toml found in ${INSTALL_DIR}; falling back to fallback shim."
    return 1
  fi
  log "Installing Rakkib via pipx from ${INSTALL_DIR}"
  pipx install --force "$INSTALL_DIR" >/dev/null 2>&1 || {
    warn "pipx install failed; falling back to fallback shim."
    return 1
  }
  log "Installed rakkib CLI via pipx"
}

install_fallback_shim() {
  local target="${HOME}/.local/bin/rakkib"
  if [[ -e "$target" && ! -L "$target" ]]; then
    warn "Skipping rakkib PATH shim because ${target} already exists and is not a symlink."
    return 0
  fi

  mkdir -p "${HOME}/.local/bin"
  cat > "$target" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="${INSTALL_DIR}/src:\${PYTHONPATH}"
exec python3 -m rakkib.cli "\$@"
EOF
  chmod +x "$target"
  log "Installed rakkib fallback CLI shim at ${target}"
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
    install_fallback_shim
  fi
  ensure_shell_path
  print_next_steps
}

main "$@"
