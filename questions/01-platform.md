# Question File 01 — Platform

**Phase 1 of 6. No writes outside the repo occur during this phase.**

---

## Instructions for the Agent

Ask the user the following questions in order. Linux runs ask three questions; Mac runs ask two because the Linux-only privilege question is skipped. Record answers into `.fss-state.yaml` under the keys specified. Do not advance to `questions/02-identity.md` until every required answer is recorded.

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

### Q2 — Linux Privilege Mode

Ask on Linux only: "Can this account use `sudo` for system installs and service setup? (`sudo`/`root`/`none`)"

Accepted answers (case-insensitive, normalize to lowercase):
- `sudo` — the agent may prompt once for the sudo password after confirmation
- `root` — the agent is already running as root or does not need sudo
- `none` — the account cannot perform system-level installs

For Mac, do not ask this question. Record `privilege_mode: sudo` by default because the Linux sudo flow does not apply.

If Linux and the user answers `none`, note that a fresh Linux install that needs Docker cannot proceed until the installer is run from a privileged account.

### Q3 — Docker Status

Ask: "Is Docker already installed and running on this machine? (y/n)"

Accepted answers: `y` or `n`. Normalize to boolean.

If the user answers `n`, note that step `steps/00-prereqs.md` will handle Docker installation before any other step runs.

---

## Record in .fss-state.yaml

```yaml
platform: linux        # or: mac
arch: amd64            # or: arm64, auto-detected from `uname -m`
privilege_mode: sudo   # Linux: sudo | root | none; Mac: sudo
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
