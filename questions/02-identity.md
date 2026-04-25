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

### Q2b — Cloudflare Zone

Ask: "Is this base domain already managed in Cloudflare in the same account you will use for this server? (y/n)"

Accepted answers: `y` or `n`. Normalize to boolean.

If `n`, explain that the domain is not yet in a Cloudflare state this installer can manage, and recommend Cloudflare primary setup (full) for most cases. Free and Pro plans should use primary setup. Tell the user to finish adding the domain to Cloudflare and reach an active zone state before relying on public DNS routing and HTTPS verification.

The agent may continue the interview and local-only setup, but must clearly state that `steps/40-cloudflare.md` and public verification in `steps/90-verify.md` cannot fully pass until the domain is managed in Cloudflare.

Record answer as `cloudflare.zone_in_cloudflare` (Phase 4 will use this value).

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
cloudflare:
  zone_in_cloudflare: true    # from Q2b
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
