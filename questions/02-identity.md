# Question File 02 — Identity

**Phase 2 of 6. No writes outside the repo occur during this phase.**

---

## Instructions for the Agent

Ask the user the following five questions in order. Validate each answer as specified before accepting it. Record all values into `.fss-state.yaml`. Do not advance to `questions/03-services.md` until all five answers are validated and recorded.

Use the `platform` value already recorded in phase 1 to set the `data_root` default.
Detect `lan_ip` from the machine instead of asking for it. On Linux, prefer `hostname -I` and record the first non-loopback IPv4 address. On Mac, use a command such as `ipconfig getifaddr en0` and fall back to another active interface if needed.

If no usable LAN IPv4 address can be detected automatically, stop and ask the user before continuing.

---

## Questions to Ask

### Q1 — Server Name

Ask: "What is your server name? (e.g. myserver — used in configs and backup manifests)"

Validation: must be non-empty, lowercase alphanumeric and hyphens only (no spaces, no dots).

### Q2 — Base Domain

Ask: "What is your base domain? (e.g. example.com — all services will be subdomains of this)"

Validation:
- Must not start with `http` or `https`
- Must contain at least one dot
- Re-ask if either condition is violated

### Q3 — Admin Username

Ask: "What is the admin username on this machine? (e.g. ubuntu — used in file paths and service ownership)"

Validation: must be non-empty.

### Q4 — Admin Email

Ask: "What is the admin email address? (used for NocoDB admin account and service notifications)"

Validation: must be non-empty and contain `@`.

### Q5 — Timezone

Ask: "What is your timezone in IANA format? (e.g. America/New_York, Europe/London, Asia/Riyadh, Asia/Tokyo, Australia/Sydney, UTC)"

Validation: must be non-empty.

---

## Record in .fss-state.yaml

```yaml
server_name: value
domain: value
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
