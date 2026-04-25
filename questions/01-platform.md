# Question File 01 — Platform

**Phase 1 of 6. No writes outside the repo occur during this phase.**

---

## Instructions for the Agent

Ask the user the following questions in order. Record answers into `.fss-state.yaml` under the keys specified. Do not advance to `questions/02-identity.md` until every required answer is recorded.

Detect `arch` from the machine instead of asking for it. Use `uname -m` and normalize as follows:
- `x86_64` -> `amd64`
- `aarch64` or `arm64` -> `arm64`

If detection returns anything else, stop and ask the user before continuing.

---

## EUID Detection

Before asking any questions, detect whether the agent is running as root:

- On Linux, check `EUID` with `id -u` or `$EUID`.
- If `EUID == 0`:
  - If `/usr/local/libexec/rakkib-root-helper` exists, call it directly: `/usr/local/libexec/rakkib-root-helper probe`.
  - Record:
    ```yaml
    privilege_mode: root
    privilege_strategy: helper
    helper:
      installed: true   # or false if absent
      version: <probe version or null>
      bootstrap_required: true  # if absent; false if already installed
    ```
  - **Skip Q2 entirely.** The install will run as root and the helper will be installed directly in Step 00.
- If `EUID != 0`:
  - Probe for the helper: `sudo -n /usr/local/libexec/rakkib-root-helper probe`.
  - If the helper is present and usable, record the same shape as above with `privilege_mode: sudo` (or derive from existing state) and continue.
  - If the helper is absent or unusable, print a single clear instruction using the agent's own absolute executable path, then stop cleanly. Do not ask Q2. Example:
    > "This installer needs root to bootstrap a narrow privilege helper on a fresh machine. Please relaunch this agent with:
    > `sudo -E /full/path/to/agent-binary`
    > Then restart the install from the beginning."
  - Do **not** fall back to `sudo -S` or password-in-chat.

On Mac, do not perform EUID detection for privilege mode. Record `privilege_mode: sudo`, `privilege_strategy: none`, and `helper.installed: false` by default because the Linux helper flow does not apply.

---

## Questions to Ask

### Q1 — Operating System

Ask: "What platform are you installing on?"

Accepted answers (case-insensitive, normalize to lowercase):
- `linux`
- `mac`

Re-ask if the user provides any other answer.

### Q2 — System Setup Access

**Ask on Linux only if `EUID != 0` and the helper is already installed and usable.**

If the helper is absent and the agent is not running as root, this question is **skipped** in favor of the relaunch instruction above.

If the helper is already present, ask:

"Rakkib needs permission to install system components like Docker and create `/srv` folders. Which option matches this machine?

1. I can approve admin prompts when asked
2. I already started this agent from a root/admin shell
3. I cannot provide admin access on this machine"

Accepted answers (case-insensitive, normalize to internal values):
- `1`, `admin prompts`, `approve`, `sudo` -> `privilege_mode: sudo`
- `2`, `root`, `root shell`, `sudo -i` -> `privilege_mode: root`
- `3`, `no`, `none`, `cannot` -> `privilege_mode: none`

Internal meaning:
- `sudo` — the helper is already present; root-required work will route through helper verbs
- `root` — the agent is running as root and will install the helper directly in Step 00
- `none` — the account cannot perform system-level installs

If Linux and the user answers `none`, note that a fresh Linux install that needs Docker cannot proceed until the installer is run from a privileged account or a machine image with the helper preinstalled.

### Q3 — Docker Status

Ask: "Is Docker already installed and running on this machine? (y/n)"

Accepted answers: `y` or `n`. Normalize to boolean.

If the user answers `n`, note that step `steps/00-prereqs.md` will handle Docker installation before any other step runs. On Linux, the documented install path is Docker's official Docker Engine for Ubuntu method routed through the privileged helper.

---

## Record in .fss-state.yaml

```yaml
platform: linux        # or: mac
arch: amd64            # or: arm64, auto-detected from `uname -m`
privilege_mode: root   # Linux: sudo | root | none; Mac: sudo
privilege_strategy: helper  # Linux: helper | root_process | none; Mac: none
helper:
  installed: true
  version: 1
  bootstrap_required: false
docker_installed: true # or: false
```

---

## Platform Context (carry forward to all subsequent phases)

These implications are not questions — record them as derived facts alongside the answers above:

**Linux:**
- `DATA_ROOT` defaults to `/srv`
- Init system: `systemd`
- Docker host IP reachable from containers: `172.18.0.1`

**Mac:**
- `DATA_ROOT` defaults to `$HOME/srv` (using `/srv` on Mac requires root and breaks Docker Desktop bind mounts)
- Init system: `launchd`
- Docker host IP reachable from containers: `host.docker.internal`

These defaults will be confirmed or overridden in `02-identity.md`.

Also record the reachable host address as `host_gateway`:

```yaml
host_gateway: 172.18.0.1        # Linux
host_gateway: host.docker.internal # Mac
```
