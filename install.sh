#!/usr/bin/env bash

set -Eeuo pipefail

REPO_URL="${RAKKIB_REPO:-https://github.com/FayaaDev/Rakkib.git}"
BRANCH="${RAKKIB_BRANCH:-main}"
RUN_DOCTOR=true
DOCTOR_ONLY=false
AGENT_MODE="${RAKKIB_AGENT:-auto}"

if [[ -z "${RAKKIB_DIR:-}" && -f "AGENT_PROTOCOL.md" && -d ".git" ]]; then
    INSTALL_DIR="$(pwd)"
else
    INSTALL_DIR="${RAKKIB_DIR:-${HOME}/Rakkib}"
fi

usage() {
    cat <<'USAGE'
Usage: install.sh [--dir <path>] [--repo <url>] [--branch <name>] [--skip-doctor] [--doctor-only]
                  [--agent <auto|opencode|claude|codex|none>] [--no-agent] [--print-prompt]

Thin Rakkib bootstrapper. It verifies basic host support, clones or updates
the installer repo, optionally runs the doctor diagnostic, installs the scoped
privilege helper on Linux (via passwordless sudo or interactive prompt), then
launches an installed coding agent with the installer prompt. If multiple
supported agents are available, it asks which one to use. If no supported agent
is available, it prints the manual prompt instead. It does not replace the
agent-driven installer workflow.

Environment overrides:
  RAKKIB_DIR       target checkout path, default: $HOME/Rakkib
  RAKKIB_REPO      git repo URL, default: https://github.com/FayaaDev/Rakkib.git
  RAKKIB_BRANCH    git branch, default: main
  RAKKIB_AGENT     agent to launch, default: auto
USAGE
}

log() {
    printf '==> %s\n' "$*"
}

warn() {
    printf 'WARNING: %s\n' "$*" >&2
}

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
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
            --skip-doctor)
                RUN_DOCTOR=false
                shift
                ;;
            --doctor-only)
                DOCTOR_ONLY=true
                shift
                ;;
            --agent)
                [[ "$#" -ge 2 ]] || die "missing value for --agent"
                AGENT_MODE="$2"
                shift 2
                ;;
            --no-agent|--print-prompt)
                AGENT_MODE="print"
                shift
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

detect_platform() {
    local kernel arch normalized_arch
    kernel="$(uname -s 2>/dev/null || true)"
    arch="$(uname -m 2>/dev/null || true)"

    case "$kernel" in
        Linux|Darwin) ;;
        *) die "unsupported OS: ${kernel:-unknown}; expected Linux or Mac" ;;
    esac

    case "$arch" in
        x86_64|amd64) normalized_arch="amd64" ;;
        aarch64|arm64) normalized_arch="arm64" ;;
        *) die "unsupported architecture: ${arch:-unknown}; expected amd64 or arm64" ;;
    esac

    log "Detected ${kernel}/${normalized_arch}"
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
            git -C "$INSTALL_DIR" checkout "$BRANCH"
        else
            git -C "$INSTALL_DIR" checkout -B "$BRANCH" "origin/${BRANCH}"
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

run_doctor() {
    local doctor="${INSTALL_DIR}/scripts/rakkib-doctor"
    [[ -x "$doctor" ]] || die "doctor script is missing or not executable: ${doctor}"

    log "Running Rakkib doctor"
    if "$doctor" --state "${INSTALL_DIR}/.fss-state.yaml"; then
        return 0
    fi

    if [[ "$DOCTOR_ONLY" == true ]]; then
        return 1
    fi

    warn "Doctor reported failures. This can be normal before Step 00 installs Docker; review the report before proceeding."
}

agent_prompt() {
    cat <<'PROMPT'
Read README.md and AGENT_PROTOCOL.md first.

Use this repo as the installer.
Ask me the question files in order.
Record answers in .fss-state.yaml.
Do not write outside the repo until Phase 6 (questions/06-confirm.md).
Use the helper-first Linux privilege flow instead of raw sudo for normal step execution.
After confirmation, execute steps/00-prereqs.md through steps/90-verify.md in numeric order, skipping optional restore-test work unless explicitly requested.
Stop on any failed Verify block and fix it before continuing.
PROMPT
}

print_agent_prompt() {
    cat <<EOF

Rakkib is ready for the agent-driven install flow.

Repo path:
  ${INSTALL_DIR}

Next step:
  cd "${INSTALL_DIR}"

  Start your coding agent with root privileges:
    sudo -E \$(command -v claude)    # or: sudo -E \$(command -v opencode), sudo -E \$(command -v codex)

  Then paste this prompt:

--- PROMPT START ---
$(agent_prompt)
--- PROMPT END ---
EOF
}

select_agent() {
    local candidate choice index
    local installed=()

    case "$AGENT_MODE" in
        auto)
            for candidate in opencode claude codex; do
                if command_exists "$candidate"; then
                    installed+=("$candidate")
                fi
            done

            if [[ "${#installed[@]}" -eq 0 ]]; then
                return 1
            fi

            if [[ "${#installed[@]}" -eq 1 ]]; then
                printf '%s\n' "${installed[0]}"
                return 0
            fi

            if [[ ! -r /dev/tty || ! -w /dev/tty ]]; then
                warn "Multiple supported agent CLIs found, but no interactive /dev/tty is available for choosing one."
                return 3
            fi

            printf '\nRakkib found these AI agent CLIs:\n\n' > /dev/tty
            index=1
            for candidate in "${installed[@]}"; do
                printf '%s. %s\n' "$index" "$(agent_label "$candidate")" > /dev/tty
                index=$((index + 1))
            done
            printf '%s. Do not launch an agent; print the prompt instead\n\n' "$index" > /dev/tty

            while true; do
                printf 'Which one do you want to use? [1-%s] ' "$index" > /dev/tty
                IFS= read -r choice < /dev/tty || return 1

                if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= index )); then
                    if (( choice == index )); then
                        return 2
                    fi
                    printf '%s\n' "${installed[$((choice - 1))]}"
                    return 0
                fi

                warn "Invalid choice: ${choice:-empty}"
            done
            ;;
        opencode|claude|codex)
            command_exists "$AGENT_MODE" || die "requested agent is not installed or not on PATH: ${AGENT_MODE}"
            printf '%s\n' "$AGENT_MODE"
            ;;
        print|none)
            return 2
            ;;
        *)
            die "unsupported agent: ${AGENT_MODE}; expected auto, opencode, claude, codex, or none"
            ;;
    esac
}

agent_label() {
    case "$1" in
        opencode) printf 'OpenCode\n' ;;
        claude) printf 'Claude Code\n' ;;
        codex) printf 'Codex\n' ;;
        *) printf '%s\n' "$1" ;;
    esac
}

launch_agent() {
    local agent prompt status

    if agent="$(select_agent)"; then
        :
    else
        status="$?"
        if [[ "$AGENT_MODE" == "auto" && "$status" -eq 1 ]]; then
            warn "No supported agent CLI found on PATH. Looked for: opencode, claude, codex."
        fi
        return 1
    fi

    if [[ ! -r /dev/tty ]]; then
        warn "No interactive /dev/tty is available; cannot launch ${agent} safely from curl|bash."
        return 1
    fi

    prompt="$(agent_prompt)"
    log "Launching ${agent} from ${INSTALL_DIR}"
    cd "$INSTALL_DIR"
    exec < /dev/tty

    case "$agent" in
        opencode)
            exec opencode . --prompt "$prompt"
            ;;
        claude)
            exec claude "$prompt"
            ;;
        codex)
            exec codex "$prompt"
            ;;
    esac
}

ensure_linux_privilege() {
    local helper="/usr/local/libexec/rakkib-root-helper"
    local installer="${INSTALL_DIR}/scripts/install-privileged-helper"
    local user
    user="$(id -un)"

    # Already have helper? Great.
    if sudo -n "$helper" probe >/dev/null 2>&1; then
        log "Privileged helper is already installed."
        return 0
    fi

    # Try passwordless sudo first (common on cloud VMs)
    if sudo -n true >/dev/null 2>&1; then
        log "Installing privileged helper with passwordless sudo..."
        if sudo -n "$installer" --admin-user "$user"; then
            log "Helper installed successfully."
            return 0
        else
            die "Failed to install privileged helper with sudo."
        fi
    fi

    # Passwordless didn't work. Check if we have a TTY for interactive prompt.
    if [[ -t 0 ]]; then
        log "Root privileges are needed to install the scoped helper."
        local pw
        printf 'sudo password: ' >&2
        read -rs pw
        printf '\n' >&2

        if printf '%s\n' "$pw" | sudo -S true >/dev/null 2>&1; then
            log "Installing privileged helper..."
            if printf '%s\n' "$pw" | sudo -S "$installer" --admin-user "$user"; then
                log "Helper installed successfully."
                return 0
            else
                die "Failed to install privileged helper with sudo."
            fi
        else
            die "Incorrect sudo password or user is not in sudoers."
        fi
    fi

    # No TTY, can't prompt. Fall back to manual relaunch instruction.
    cat >&2 <<'EOF'

ERROR: Root privileges are required on Linux to install the scoped helper.

This bootstrapper could not use passwordless sudo and has no TTY to prompt
for a password. Please run the bootstrapper with sudo:

  curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | sudo bash

Or relaunch the agent manually with:

  sudo -E $(command -v claude)    # or opencode, codex

EOF
    exit 1
}

main() {
    parse_args "$@"
    detect_platform
    ensure_tooling
    prepare_repo

    if [[ "$RUN_DOCTOR" == true ]]; then
        run_doctor
    fi

    # On Linux, bootstrap the helper before launching the agent so the agent
    # never has to break the conversation for a privilege prompt.
    if [[ "$DOCTOR_ONLY" == false && "$(uname -s)" == "Linux" && "${EUID:-$(id -u)}" -ne 0 ]]; then
        ensure_linux_privilege
    fi

    if [[ "$DOCTOR_ONLY" == false ]]; then
        if [[ "$AGENT_MODE" == "print" || "$AGENT_MODE" == "none" ]]; then
            print_agent_prompt
        elif ! launch_agent; then
            print_agent_prompt
        fi
    fi
}

main "$@"
