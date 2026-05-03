# Question File 01 — Platform

**Phase 1 of 6. No writes outside the repo occur during this phase.**

## AgentSchema

```yaml
schema_version: 1
phase: 1
reads_state: []
writes_state:
  - platform
  - arch
  - privilege_mode
  - privilege_strategy
  - docker_installed
  - host_gateway
fields:
  - id: arch
    type: derived
    source: host
    detect:
      command: uname -m
      normalize:
        x86_64: amd64
        aarch64: arm64
        arm64: arm64
    records:
      - arch
  - id: privilege_context
    type: derived
    source: host
    when: platform == linux
    detect:
      command: id -u
      normalize:
        "0":
          privilege_mode: root
          privilege_strategy: root_process
        default:
          privilege_mode: sudo
          privilege_strategy: on_demand
    records:
      - privilege_mode
      - privilege_strategy
  - id: mac_privilege_context
    type: derived
    source: host
    when: platform == mac
    value:
      privilege_mode: sudo
      privilege_strategy: on_demand
    records:
      - privilege_mode
      - privilege_strategy
  - id: platform
    type: single_select
    prompt: What platform are you installing on?
    canonical_values: [linux, mac]
    normalize: lowercase
    aliases:
      linux: [linux]
      mac: [mac, macos, osx, darwin]
    records:
      - platform
  - id: docker_installed
    type: confirm
    prompt: Is Docker already installed and running on this machine? [y/N]
    default: true
    accepted_inputs:
      y: true
      n: false
      "yes": true
      "no": false
    records:
      - docker_installed
  - id: host_gateway
    type: derived
    source: prior_answer
    derive_from: platform
    value:
      linux: 172.18.0.1
      mac: host.docker.internal
    records:
      - host_gateway
```

---

## Instructions for the Agent

Ask the user the following questions in order. Record answers into `.fss-state.yaml` under the keys specified. Do not advance to `questions/02-identity.md` until every required answer is recorded.

Detect `arch` from the machine instead of asking for it. Use `uname -m` and normalize as follows:
- `x86_64` -> `amd64`
- `aarch64` or `arm64` -> `arm64`

If detection returns anything else, stop and ask the user before continuing.

---

## EUID Detection

Before asking any questions on Linux, detect whether the agent is running as root:

- On Linux, check `EUID` with `id -u` or `$EUID`.
- If `EUID != 0`:
  - Record:
    ```yaml
    privilege_mode: sudo
    privilege_strategy: on_demand
    ```
  - Continue the interview as the normal admin user. Privileged system setup will be requested with `sudo` only after Phase 6 confirmation.
- If `EUID == 0`:
  - Record:
    ```yaml
    privilege_mode: root
    privilege_strategy: root_process
    ```
  - Warn that running the full agent session as root is intended only for repair/debug sessions. If `SUDO_USER` is set, offer to restart `rakkib init` as that admin user before continuing.
  - Do **not** fall back to `sudo -S`, do not ask for a password in chat, and do not store sudo credentials.

On Mac, do not perform Linux root enforcement. Record `privilege_mode: sudo` and `privilege_strategy: on_demand`.

---

## Questions to Ask

### Q1 — Operating System

Ask: "What platform are you installing on?"

Accepted answers (case-insensitive, normalize to lowercase):
- `linux`
- `mac`
- `macos` -> `mac`
- `osx` -> `mac`
- `darwin` -> `mac`

Re-ask if the user provides any other answer.

### Q2 — Docker Status

Ask: "Is Docker already installed and running on this machine? [y/N]"

Accepted answers: `y` or `n`. Normalize to boolean.

If the user answers `n`, note that step `steps/00-prereqs.md` will handle Docker installation before any other step runs. On Linux, the documented install path is Docker's official Docker Engine for Ubuntu method run directly by the root installer process.

---

## Record in .fss-state.yaml

```yaml
platform: linux        # or: mac
arch: amd64            # or: arm64, auto-detected from `uname -m`
privilege_mode: sudo   # normal Linux/Mac flow; root only for repair/debug sessions
privilege_strategy: on_demand  # request sudo only for specific post-confirmation actions
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
