# Question File 02 — Identity

**Phase 2 of 6. No writes outside the repo occur during this phase.**

## AgentSchema

```yaml
schema_version: 1
phase: 2
reads_state:
  - platform
  - privilege_mode
  - host_gateway
writes_state:
  - server_name
  - domain
  - exposure_mode
  - cloudflare.zone_in_cloudflare
  - admin_user
  - admin_email
  - lan_ip
  - tz
  - data_root
  - docker_net
  - backup_dir
  - host_gateway
fields:
  - id: server_name
    type: text
    prompt: What is your server name? (e.g. myserver — used in configs and backup manifests)
    validate:
      pattern: ^[a-z0-9-]+$
      message: Use lowercase letters, numbers, and hyphens only.
    records:
      - server_name
  - id: exposure_mode
    type: single_select
    prompt: How should services be exposed?
    canonical_values: [internal, cloudflare]
    aliases:
      internal: [Internal Docker network, private, local]
      cloudflare: [Cloudflare tunnel, public]
    records:
      - exposure_mode
  - id: internal_domain
    type: derived
    when: exposure_mode == internal
    value: localhost
    records:
      - domain
  - id: domain
    type: text
    when: exposure_mode == cloudflare
    prompt: What is your base domain? (e.g. example.com — all services will be subdomains of this)
    validate:
      pattern: ^(?!https?://).+\..+$
      message: Use a bare domain like example.com, without http:// or https://.
    records:
      - domain
  - id: zone_in_cloudflare
    type: confirm
    when: exposure_mode == cloudflare
    prompt: Is this base domain already managed in Cloudflare in the same account you will use for this server? [y/N]
    default: true
    accepted_inputs:
      y: true
      n: false
      "yes": true
      "no": false
    records:
      - cloudflare.zone_in_cloudflare
  - id: admin_user
    type: derived
    source: host
    detect:
      linux:
        - python3
        - -c
        - |
          import getpass, os
          user = os.environ.get("SUDO_USER")
          print(user if user and user != "root" else getpass.getuser())
      mac: id -un
    records:
      - admin_user
  - id: admin_email
    type: derived
    source: prior_answer
    derive_from: [admin_user, domain]
    template: "{{admin_user}}@{{domain}}"
    records:
      - admin_email
  - id: tz
    type: derived
    source: host
    detect:
      linux:
        - python3
        - -c
        - |
          from pathlib import Path
          import subprocess

          result = subprocess.run(["timedatectl", "show", "-p", "Timezone", "--value"], capture_output=True, text=True)
          timezone = result.stdout.strip()
          if not timezone:
              timezone = Path("/etc/timezone").read_text().strip() if Path("/etc/timezone").exists() else "UTC"
          print(timezone or "UTC")
      mac:
        - python3
        - -c
        - |
          import subprocess

          result = subprocess.run(["systemsetup", "-gettimezone"], capture_output=True, text=True)
          output = result.stdout.strip()
          print(output.split(":", 1)[1].strip() if ":" in output else "UTC")
    records:
      - tz
  - id: lan_ip
    type: derived
    source: host
    detect:
      linux: hostname -I
      mac: ipconfig getifaddr en0
    normalize: first_non_loopback_ipv4
    records:
      - lan_ip
  - id: data_root
    type: derived
    source: prior_answer
    derive_from: platform
    value:
      linux: /srv
      mac: $HOME/srv
    records:
      - data_root
  - id: docker_net
    type: derived
    value: caddy_net
    records:
      - docker_net
  - id: backup_dir
    type: derived
    source: prior_answer
    derive_from: data_root
    template: "{{data_root}}/backups"
    records:
      - backup_dir
```

---

## Instructions for the Agent

Ask the user the questions below in order. Record all values into `.fss-state.yaml`.

The following values are auto-derived and must not be prompted for:

- `admin_user` (detected from the host; prefers `SUDO_USER` when present)
- `admin_email` (derived; may be overridden later when NocoDB is selected)
- `tz` (detected from the host; falls back to `UTC`)

Use the `platform` value already recorded in phase 1 to set the `data_root` default.
Detect `lan_ip` from the machine instead of asking for it. On Linux, prefer `hostname -I` and record the first non-loopback IPv4 address. On Mac, use a command such as `ipconfig getifaddr en0` and fall back to another active interface if needed.

If no usable LAN IPv4 address can be detected automatically, stop and ask the user before continuing.

---

## Questions to Ask

### Q1 — Server Name

Ask: "What is your server name? (e.g. myserver — used in configs and backup manifests)"

Validation: must be non-empty, lowercase alphanumeric and hyphens only (no spaces, no dots).

### Q2 — Exposure Mode

Ask: "How should services be exposed?"

Default/recommended: `internal`.

Options:
- `internal`: keep services on the private Docker network; do not create Caddy, Cloudflare tunnels, or DNS routes.
- `cloudflare`: publish explicit service hostnames through a Cloudflare tunnel.

### Q2b — Base Domain

Ask this only when `exposure_mode` is `cloudflare`.

Ask: "What is your base domain? (e.g. example.com — all services will be subdomains of this)"

Validation:
- Must not start with `http` or `https`
- Must contain at least one dot
- Re-ask if either condition is violated

For `internal`, record `domain: localhost` without prompting. Internal mode does not deploy Caddy host routes, so this value is only a harmless placeholder for state compatibility.

### Q2c — Cloudflare Zone

Ask this only when `exposure_mode` is `cloudflare`.

Ask: "Is this base domain already managed in Cloudflare in the same account you will use for this server? [y/N]"

Accepted answers: `y` or `n`. Normalize to boolean.

If `n`, explain that the domain is not yet in a Cloudflare state this installer can manage, and recommend Cloudflare primary setup (full) for most cases. Free and Pro plans should use primary setup. Tell the user to finish adding the domain to Cloudflare and reach an active zone state before relying on public DNS routing and HTTPS verification.

The agent may continue the interview and local-only setup, but must clearly state that `steps/40-cloudflare.md` and public verification in `steps/90-verify.md` cannot fully pass until the domain is managed in Cloudflare.

Record answer as `cloudflare.zone_in_cloudflare` (Phase 4 will use this value).

---

## Record in .fss-state.yaml

```yaml
server_name: value
domain: value
exposure_mode: internal
cloudflare:
  zone_in_cloudflare: true    # only when exposure_mode is cloudflare
admin_user: value
admin_email: value
lan_ip: value
tz: value
data_root: /srv           # default for Linux; use $HOME/srv for Mac (from phase 1)
docker_net: caddy_net
backup_dir: "{{data_root}}/backups"
host_gateway: 172.18.0.1 # or: host.docker.internal from phase 1
```

Note: `data_root` is derived from `platform` (phase 1). Do not ask the user for it — set it automatically:
- `platform: linux` → `data_root: /srv`
- `platform: mac` → `data_root: $HOME/srv`

Note: `lan_ip` is derived from the host network configuration in phase 2. Do not ask the user for it unless auto-detection fails.
