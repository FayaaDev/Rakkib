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
  - host_gateway
fields:
  - id: platform
    type: derived
    source: host
    records:
      - platform
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

Auto-detect platform from the machine and record answers into `.fss-state.yaml` under the keys specified. Do not advance to `questions/02-identity.md` until every required answer is recorded.

Detect platform from the machine instead of asking for it:
- Linux -> `linux`
- Darwin/macOS -> `mac`

If detection returns anything else, stop with an actionable unsupported-platform error.

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

## Record in .fss-state.yaml

```yaml
platform: linux        # or: mac, auto-detected from the host
arch: amd64            # or: arm64, auto-detected from `uname -m`
privilege_mode: sudo   # normal Linux flow; root only for repair/debug sessions
privilege_strategy: on_demand  # request sudo only for specific post-confirmation actions
```

---

## Platform Context (carry forward to all subsequent phases)

These implications are not questions — record them as derived facts alongside the answers above:

**Linux:**
- `DATA_ROOT` defaults to `/srv`
- Init system: `systemd`
- Docker host IP reachable from containers: `172.18.0.1`

**Mac:**
- `DATA_ROOT` defaults to `$HOME/srv` (using `/srv` on Mac requires root and can break Docker bind mounts)
- Init system: `launchd`
- Docker host IP reachable from containers: `host.docker.internal`

These defaults will be confirmed or overridden in `02-identity.md`.

Also record the reachable host address as `host_gateway`:

```yaml
host_gateway: 172.18.0.1        # Linux
host_gateway: host.docker.internal # Mac
```
