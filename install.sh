#!/usr/bin/env bash

set -Eeuo pipefail

REPO_URL="${RAKKIB_REPO:-https://github.com/FayaaDev/Rakkib.git}"
BRANCH="${RAKKIB_BRANCH:-main}"
BOOTSTRAP_URL="${RAKKIB_BOOTSTRAP_URL:-https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh}"
RUN_DOCTOR=true
DOCTOR_ONLY=false
AGENT_MODE="${RAKKIB_AGENT:-auto}"
PRINT_PROMPT_ONLY=false
ORIGINAL_ARGS=()
BOOTSTRAP_USER=""
BOOTSTRAP_USER_HOME=""

if [[ "${EUID:-$(id -u)}" -eq 0 && -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    BOOTSTRAP_USER="$SUDO_USER"
    BOOTSTRAP_USER_HOME="$(getent passwd "$BOOTSTRAP_USER" 2>/dev/null | cut -d: -f6 || true)"
fi

if [[ -z "${RAKKIB_DIR:-}" && -f "AGENT_PROTOCOL.md" && -d ".git" ]]; then
    INSTALL_DIR="$(pwd)"
elif [[ -z "${RAKKIB_DIR:-}" && -n "$BOOTSTRAP_USER_HOME" ]]; then
    INSTALL_DIR="${BOOTSTRAP_USER_HOME}/Rakkib"
else
    INSTALL_DIR="${RAKKIB_DIR:-${HOME}/Rakkib}"
fi

usage() {
    cat <<'USAGE'
Usage: install.sh [--dir <path>] [--repo <url>] [--branch <name>]
                  [--skip-doctor] [--doctor-only]
                  [--agent <auto|opencode|claude|codex|none>] [--no-agent] [--print-prompt]
                  [--sudo-preauth <auto|always|never>]

Thin Rakkib remote bootstrapper. It verifies basic host support, clones or
updates the installer repo as the normal admin user when possible, installs a
user-scoped `rakkib` shim, then prints the next command to run.

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

run_as_bootstrap_user() {
    if [[ -n "$BOOTSTRAP_USER" ]]; then
        sudo -u "$BOOTSTRAP_USER" -H "$@"
    else
        "$@"
    fi
}

shell_quote() {
    printf '%q' "$1"
}

rerun_command() {
    printf 'curl -fsSL %s | bash' "$BOOTSTRAP_URL"
    if [[ "${#ORIGINAL_ARGS[@]}" -gt 0 ]]; then
        printf ' -s --'
        local arg
        for arg in "${ORIGINAL_ARGS[@]}"; do
            printf ' %s' "$(shell_quote "$arg")"
        done
    fi
    printf '\n'
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
            --no-agent)
                AGENT_MODE="print"
                shift
                ;;
            --print-prompt)
                AGENT_MODE="print"
                PRINT_PROMPT_ONLY=true
                shift
                ;;
            --agent)
                [[ "$#" -ge 2 ]] || die "missing value for --agent"
                AGENT_MODE="$2"
                shift 2
                ;;
            --sudo-preauth)
                [[ "$#" -ge 2 ]] || die "missing value for --sudo-preauth"
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

ensure_linux_root() {
    [[ "$(uname -s 2>/dev/null || true)" == "Linux" ]] || return 0
    [[ "${EUID:-$(id -u)}" -eq 0 ]] && return 0

    cat >&2 <<EOF

ERROR: This legacy root guard should not be reached in the current Rakkib CLI flow.

Re-run the bootstrapper as your normal admin user:

  $(rerun_command)

Rakkib requests sudo only after Phase 6 confirmation for specific privileged setup actions.

EOF
    exit 1
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
On Linux, run the agent as the normal admin user and request sudo only for specific privileged setup actions after confirmation.
After confirmation, execute steps/00-prereqs.md through steps/90-verify.md in numeric order, skipping optional restore-test work unless explicitly requested.
Stop on any failed Verify block and fix it before continuing.
PROMPT
}

print_agent_prompt() {
    cat <<EOF

Rakkib is ready for the agent-driven install flow.

Repo path:
  ${INSTALL_DIR}

Linux entrypoint:
  $(rerun_command)

Paste this prompt if your agent was not launched automatically:

--- PROMPT START ---
$(agent_prompt)
--- PROMPT END ---
EOF
}

agent_label() {
    case "$1" in
        opencode) printf 'OpenCode\n' ;;
        claude) printf 'Claude Code\n' ;;
        codex) printf 'Codex\n' ;;
        *) printf '%s\n' "$1" ;;
    esac
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

offer_install_opencode() {
    local answer

    if [[ ! -r /dev/tty || ! -w /dev/tty ]]; then
        cat >&2 <<'EOF'
WARNING: No supported agent CLI found on PATH. Looked for: opencode, claude, codex.

No interactive terminal is available to confirm installing OpenCode. Install it manually with:

  curl -fsSL https://opencode.ai/install | bash

Then re-run the Rakkib bootstrapper.

EOF
        return 1
    fi

    cat > /dev/tty <<'EOF'

Rakkib could not find a supported agent CLI on PATH. Looked for: opencode, claude, codex.

Would you like to install OpenCode now?
Installer command: curl -fsSL https://opencode.ai/install | bash

EOF

    while true; do
        printf 'Install OpenCode? [y/N] ' > /dev/tty
        IFS= read -r answer < /dev/tty || return 1
        case "$answer" in
            y|Y|yes|YES|Yes)
                log "Installing OpenCode"
                curl -fsSL https://opencode.ai/install | bash
                hash -r 2>/dev/null || true
                ensure_opencode_on_path || die "OpenCode installer completed, but opencode was not found in PATH or the expected ~/.opencode/bin location. Add it to PATH, then re-run the Rakkib bootstrapper."
                return 0
                ;;
            ''|n|N|no|NO|No)
                warn "OpenCode was not installed. Install opencode, claude, or codex, then re-run the Rakkib bootstrapper."
                return 1
                ;;
            *)
                warn "Invalid choice: ${answer:-empty}"
                ;;
        esac
    done
}

ensure_opencode_on_path() {
    command_exists opencode && return 0

    local candidate admin_home
    local candidates=("${HOME}/.opencode/bin")

    if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
        admin_home="$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f6 || true)"
        if [[ -n "$admin_home" ]]; then
            candidates+=("${admin_home}/.opencode/bin")
        fi
    fi

    candidates+=("/root/.opencode/bin")

    for candidate in "${candidates[@]}"; do
        if [[ -x "${candidate}/opencode" ]]; then
            export PATH="${candidate}:${PATH}"
            return 0
        fi
    done

    return 1
}

launch_agent() {
    local agent prompt status

    if agent="$(select_agent)"; then
        :
    else
        status="$?"
        if [[ "$AGENT_MODE" == "auto" && "$status" -eq 1 ]] && offer_install_opencode; then
            agent="opencode"
        else
            return 1
        fi
    fi

    if [[ ! -r /dev/tty ]]; then
        warn "No interactive /dev/tty is available; cannot launch ${agent} safely."
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
    [[ -n "$(run_as_bootstrap_user git -C "$INSTALL_DIR" status --porcelain 2>/dev/null)" ]]
}

prepare_repo() {
    if [[ -d "${INSTALL_DIR}/.git" ]]; then
        log "Using existing checkout: ${INSTALL_DIR}"
        if repo_has_local_changes; then
            warn "Existing checkout has local changes; skipping automatic update."
            return 0
        fi

        log "Updating existing checkout from origin/${BRANCH}"
        run_as_bootstrap_user git -C "$INSTALL_DIR" fetch origin "$BRANCH"
        if run_as_bootstrap_user git -C "$INSTALL_DIR" show-ref --verify --quiet "refs/heads/${BRANCH}"; then
            run_as_bootstrap_user git -C "$INSTALL_DIR" checkout "$BRANCH"
        else
            run_as_bootstrap_user git -C "$INSTALL_DIR" checkout -B "$BRANCH" "origin/${BRANCH}"
        fi
        run_as_bootstrap_user git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
        return 0
    fi

    if [[ -e "$INSTALL_DIR" ]] && ! is_empty_dir "$INSTALL_DIR"; then
        die "target path exists and is not an empty git checkout: ${INSTALL_DIR}"
    fi

    run_as_bootstrap_user mkdir -p "$(dirname "$INSTALL_DIR")"
    log "Cloning ${REPO_URL} into ${INSTALL_DIR}"
    run_as_bootstrap_user git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
}

install_cli_shim() {
    local user_home target
    user_home="${BOOTSTRAP_USER_HOME:-${HOME}}"
    target="${user_home}/.local/bin/rakkib"

    if [[ -e "$target" && ! -L "$target" ]]; then
        warn "Skipping rakkib PATH shim because ${target} already exists and is not a symlink."
        return 0
    fi

    run_as_bootstrap_user mkdir -p "${user_home}/.local/bin"
    run_as_bootstrap_user ln -sfn "${INSTALL_DIR}/bin/rakkib" "$target"
    log "Installed rakkib CLI shim at ${target}"
}

print_next_steps() {
    local cli="${INSTALL_DIR}/bin/rakkib"
    local user_home target

    [[ -x "$cli" ]] || die "rakkib CLI is missing or not executable: ${cli}"

    user_home="${BOOTSTRAP_USER_HOME:-${HOME}}"
    target="${user_home}/.local/bin/rakkib"

    if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        warn "Do not run rakkib init as root unless repairing a broken install. Switch to your normal admin user first."
    fi

    cat <<EOF

Rakkib is installed.

Repo:
  ${INSTALL_DIR}

CLI:
  ${target}

Next step:
  rakkib init

If rakkib is not on PATH yet, run:
  ${target} init

EOF
}

main() {
    ORIGINAL_ARGS=("$@")
    parse_args "$@"
    detect_platform
    ensure_tooling
    prepare_repo
    install_cli_shim
    print_next_steps
}

main "$@"
