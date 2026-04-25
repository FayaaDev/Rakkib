# Question File 01 — Platform

**Phase 1 of 6. No writes outside the repo occur during this phase.**

---

## Instructions for the Agent

Ask the user the following questions in order. Linux runs ask three questions; Mac runs ask two because the Linux-only system setup access question is skipped. Record answers into `.fss-state.yaml` under the keys specified. Do not advance to `questions/02-identity.md` until every required answer is recorded.

On Linux, also detect whether `/usr/local/libexec/rakkib-root-helper` is already installed and usable:
- If running as root, call `/usr/local/libexec/rakkib-root-helper probe` directly when the file exists.
- If running unprivileged, try `sudo -n /usr/local/libexec/rakkib-root-helper probe`.
- If the helper is absent or unusable, record that Step 00 must bootstrap it before any root-required work continues.

Detect `arch` from the machine instead of asking for it. Use `uname -m` and normalize as follows:
- `x86_64` -> `amd64`
- `aarch64` or `arm64` -> `arm64`

If detection returns anything else, stop and ask the user before continuing.

---

## Questions to Ask

### Q1 — Operating System

Ask: "What platform are you installing on?"

Accepted answers (case-insensitive, normalize to lowercase):
- `linux`
- `mac`

Re-ask if the user provides any other answer.

### Q2 — System Setup Access

Ask on Linux only:

"Rakkib needs permission to install system components like Docker and create `/srv` folders. Which option matches this machine?

1. I can approve admin prompts when asked
2. I already started this agent from a root/admin shell
3. I cannot provide admin access on this machine"

Accepted answers (case-insensitive, normalize to internal values):
- `1`, `admin prompts`, `approve`, `sudo` -> `privilege_mode: sudo`
- `2`, `root`, `root shell`, `sudo -i` -> `privilege_mode: root`
- `3`, `no`, `none`, `cannot` -> `privilege_mode: none`

Internal meaning:
- `sudo` — the installer may need one bootstrap trust event in Step 00 to install or unlock the helper
- `root` — the agent is already running as root or does not need sudo
- `none` — the account cannot perform system-level installs

For Mac, do not ask this question. Record `privilege_mode: sudo`, `privilege_strategy: none`, and `helper.installed: false` by default because the Linux helper flow does not apply.

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
privilege_mode: sudo   # Linux: sudo | root | none; Mac: sudo
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
