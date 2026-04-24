# Question File 01 — Platform

**Phase 1 of 6. No writes outside the repo occur during this phase.**

---

## Instructions for the Agent

Ask the user the following three questions in order. Record answers into `.fss-state.yaml` under the keys specified. Do not advance to `questions/02-identity.md` until all three answers are recorded.

---

## Questions to Ask

### Q1 — Operating System

Ask: "What platform are you installing on?"

Accepted answers (case-insensitive, normalize to lowercase):
- `linux`
- `mac`

Re-ask if the user provides any other answer.

### Q2 — CPU Architecture

Ask: "What CPU architecture is this machine?"

Accepted answers (case-insensitive, normalize to lowercase):
- `amd64` — standard x86-64 (most Linux servers, Intel Macs)
- `arm64` — Apple Silicon (M1/M2/M3/M4 Macs) or ARM Linux boards

Re-ask if the user provides any other answer.

### Q3 — Docker Status

Ask: "Is Docker already installed and running on this machine? (y/n)"

Accepted answers: `y` or `n`. Normalize to boolean.

If the user answers `n`, note that step `steps/00-prereqs.md` will handle Docker installation before any other step runs.

---

## Record in .fss-state.yaml

```yaml
platform: linux        # or: mac
arch: amd64            # or: arm64
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
