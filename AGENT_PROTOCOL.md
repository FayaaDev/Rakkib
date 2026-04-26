# Agent Protocol

This file defines the exact operating procedure for any coding agent using this repository as an installer.

## Global Rules

1. Read `AGENT_PROTOCOL.md`, `registry.yaml`, `lib/placeholders.md`, and the current question file before acting.
2. Use `.fss-state.yaml` as the single source of truth for collected answers and derived values.
3. Do not write outside the repo during Phases 1 through 6.
4. Ask questions exactly in order. Validate and normalize answers before recording them. When a value is marked as host-detected, run the required local command instead of asking the user.
5. Do not skip required phases even if values seem obvious.
6. After confirmation, execute the step files in numeric order.
7. Stop on any failed `## Verify` block. Fix the issue before advancing.
8. Prefer minimal edits on the target machine. Follow `lib/idempotency.md` for every re-apply and preserve existing user data or secrets unless explicitly replacing them.
9. Never rotate an existing `N8N_ENCRYPTION_KEY`.

## State File Shape

Maintain `.fss-state.yaml` with plain key/value data only. Keep it easy to diff and easy to edit by hand.

Expected high-level sections:

```yaml
platform: linux
arch: amd64
privilege_mode: sudo
privilege_strategy: on_demand
docker_installed: true
data_root: /srv
docker_net: caddy_net
backup_dir: /srv/backups
host_gateway: 172.18.0.1
server_name: myserver
domain: example.com
admin_user: ubuntu
admin_email: admin@example.com
lan_ip: 192.168.1.100
tz: UTC
selected_services: [n8n, immich]
host_addons: [vergo_terminal]
subdomains:
  nocodb: nocodb
  n8n: n8n
  immich: immich
  transfer: transfer
  hermes: hermes
cloudflare:
  zone_in_cloudflare: true
  auth_method: browser_login
  headless: false
  tunnel_strategy: new
  tunnel_name: myserver
  ssh_subdomain: ssh
  tunnel_uuid: null
  tunnel_creds_host_path: null
  tunnel_creds_container_path: null
claw_gateway_port: 18789
hermes_dashboard_port: 9119
cloudflared_metrics_port: 20241
secrets:
  mode: generate
confirmed: false
```

Derived value rules:

- Detect `arch` from the host with `uname -m` during Phase 1 and normalize it to `amd64` or `arm64` before recording it.
- Detect `lan_ip` from the host during Phase 2 and record the first usable LAN IPv4 address before rendering templates.
- Always derive `claw_gateway_port` as `18789` unless the repo is explicitly changed to ask for a different value.
- Always derive `hermes_dashboard_port` as `9119` unless the repo is explicitly changed to ask for a different value.
- Always derive `cloudflared_metrics_port` as `20241` unless the repo is explicitly changed to ask for a different value.
- If `hermes` is selected, `authentik` must remain in `foundation_services`; do not expose the Hermes dashboard without Authentik protection in v1.
- Record Cloudflare auth as `cloudflare.auth_method` with one of `browser_login`, `api_token`, or `existing_tunnel`. Use `browser_login` as the normal path and record `cloudflare.headless` as `true` or `false` for new tunnels.
- On Linux, the installer orchestration should run as the normal admin user. Record `privilege_mode: sudo` and `privilege_strategy: on_demand` unless the user is intentionally repairing from a root shell.
- If Linux is running as root through `sudo` with `SUDO_USER` set, prefer re-running `rakkib init` as `SUDO_USER` before launching an agent. Do not run the full AI agent session as root by default.
- On Mac, record `privilege_mode: sudo` and `privilege_strategy: on_demand`.
- When `cloudflare.tunnel_uuid` is known, derive and record:
  - `cloudflare.tunnel_creds_host_path: {{DATA_ROOT}}/data/cloudflared/<tunnel_uuid>.json`
  - `cloudflare.tunnel_creds_container_path: /home/nonroot/.cloudflared/<tunnel_uuid>.json`
- Render templates only after every placeholder they need has either a collected value or a deterministic derived value recorded in `.fss-state.yaml`.

## Render Context Rules

Before rendering any template, flatten `.fss-state.yaml` into a direct placeholder map. Do not guess names and do not render from nested keys implicitly.

Required direct mappings:

- `server_name` -> `{{SERVER_NAME}}`
- `domain` -> `{{DOMAIN}}`
- `admin_user` -> `{{ADMIN_USER}}`
- `admin_email` -> `{{ADMIN_EMAIL}}`
- `lan_ip` -> `{{LAN_IP}}`
- `tz` -> `{{TZ}}`
- `data_root` -> `{{DATA_ROOT}}`
- `docker_net` -> `{{DOCKER_NET}}`
- `host_gateway` -> `{{HOST_GATEWAY}}`
- `backup_dir` -> `{{BACKUP_DIR}}`
- `claw_gateway_port` -> `{{CLAW_GATEWAY_PORT}}`
- `hermes_dashboard_port` -> `{{HERMES_DASHBOARD_PORT}}`
- `cloudflared_metrics_port` -> `{{CLOUDFLARED_METRICS_PORT}}`

Nested mappings:

- `cloudflare.tunnel_uuid` -> `{{TUNNEL_UUID}}`
- `cloudflare.ssh_subdomain` -> `{{SSH_SUBDOMAIN}}`
- `cloudflare.tunnel_creds_host_path` -> `{{TUNNEL_CREDS_HOST_PATH}}`
- `cloudflare.tunnel_creds_container_path` -> `{{TUNNEL_CREDS_CONTAINER_PATH}}`
- `subdomains.nocodb` -> `{{NOCODB_SUBDOMAIN}}`
- if `n8n` is selected: `subdomains.n8n` -> `{{N8N_SUBDOMAIN}}`
- if `dbhub` is selected: `subdomains.dbhub` -> `{{DBHUB_SUBDOMAIN}}`
- if `immich` is selected: `subdomains.immich` -> `{{IMMICH_SUBDOMAIN}}`
- if `transfer` is selected: `subdomains.transfer` -> `{{TRANSFER_SUBDOMAIN}}`
- if `openclaw` is selected: `subdomains.claw` -> `{{OPENCLAW_SUBDOMAIN}}`
- if `hermes` is selected: `subdomains.hermes` -> `{{HERMES_SUBDOMAIN}}`

Secrets mapping:

- Every key under `secrets.values` maps directly to the same placeholder name.
- Example: `secrets.values.POSTGRES_PASSWORD` -> `{{POSTGRES_PASSWORD}}`
- Example: `secrets.values.N8N_ENCRYPTION_KEY` -> `{{N8N_ENCRYPTION_KEY}}`

Derived multiline placeholders:

- Build `{{SERVICE_SUMMARY_LINES}}` before rendering `templates/agent-memory/SERVER_README.md.tmpl`.
- It must always include these lines:
  - `- Caddy`
  - `- Cloudflared`
  - `- PostgreSQL`
  - `- NocoDB at https://{{NOCODB_SUBDOMAIN}}.{{DOMAIN}}`
- Append optional lines only for selected services:
  - `- n8n at https://{{N8N_SUBDOMAIN}}.{{DOMAIN}}`
  - `- DBHub at https://{{DBHUB_SUBDOMAIN}}.{{DOMAIN}}`
  - `- Immich at https://{{IMMICH_SUBDOMAIN}}.{{DOMAIN}}`
  - `- transfer.sh at https://{{TRANSFER_SUBDOMAIN}}.{{DOMAIN}}`
  - `- OpenClaw at https://{{OPENCLAW_SUBDOMAIN}}.{{DOMAIN}}`
  - `- Hermes at https://{{HERMES_SUBDOMAIN}}.{{DOMAIN}}`
- Build `{{HOST_ADDON_SUMMARY_LINES}}` before rendering `templates/agent-memory/SERVER_README.md.tmpl`.
- If no host addons are selected, set it to `- None`.
- If `vergo_terminal` is selected, include `- VErgo Terminal shell environment`.

Rendering guardrails:

- Do not render templates for unselected optional services.
- Do not leave unresolved placeholders in rendered target-machine files.
- If a required placeholder is missing from the render context, stop and fix the state before continuing.

## Phase Order

### Phase 1
Run `questions/01-platform.md`.

### Phase 2
Run `questions/02-identity.md`.

### Phase 3
Run `questions/03-services.md` to collect services and host addons.

### Phase 4
Run `questions/04-cloudflare.md`.

### Phase 5
Run `questions/05-secrets.md`.

### Phase 6
Run `questions/06-confirm.md`.

Only after `confirmed: true` may the agent modify the target machine.

## Execution Order

After confirmation, run these step files in numeric order:

1. `steps/00-prereqs.md`
2. `steps/10-layout.md`
3. `steps/30-caddy.md`
4. `steps/40-cloudflare.md`
5. `steps/50-postgres.md`
6. `steps/60-services.md`
7. `steps/70-host-agents.md`
8. `steps/72-host-customization.md`
9. `steps/80-cron-jobs.md`
10. `steps/90-verify.md`

Run `docs/runbooks/restore-test.md` only when explicitly performing a restore dry run or restore round-trip test. It is not part of the first-install step sequence.

## Rendering Rules

1. Render by direct placeholder substitution only.
2. Do not introduce a separate templating tool unless the user asks.
3. Render only the files required by the selected services.
4. Keep generated secrets out of git-tracked files outside `.fss-state.yaml`.
5. When a file already exists on the target machine, read it first and preserve any values that must not rotate.
6. For Cloudflared, always normalize the credentials JSON to `{{DATA_ROOT}}/data/cloudflared/<tunnel_uuid>.json` on the host and render the in-container path `/home/nonroot/.cloudflared/<tunnel_uuid>.json` into `config.yml`.
7. For SSH over Cloudflare, always use the recorded custom subdomain value rather than assuming `ssh`.
8. A local host `cloudflared` CLI is required for tunnel login, creation, and DNS routing. The container image alone is not enough for Step 40.
9. If the host `cloudflared` CLI is missing, install it during Step 00 into `~/.local/bin/cloudflared` and ensure later steps invoke it through `PATH` or the absolute path.
10. Do not ask for or store a Cloudflare API token in `.fss-state.yaml` during the normal flow. Prefer `cloudflared tunnel login`; on headless servers, tell the user to open the printed login URL on another device.
11. If `cloudflare.auth_method` is `api_token`, request the token only during Step 40, use it as a temporary environment variable, and unset it after Cloudflare work is complete. Do not persist the raw token in `.fss-state.yaml`.
12. If `secrets.mode` is `generate`, generate each missing secret immediately before the first step that needs it, then write it back into `.fss-state.yaml` before rendering any file that uses it.
13. If `cloudflare.zone_in_cloudflare` is `false`, help the user complete Cloudflare zone setup using the official docs before treating public DNS routing or HTTPS verification as complete. Do not mark the deployment fully successful while Step 40 DNS routing or Step 90 public HTTPS checks are still blocked by missing Cloudflare zone ownership.

## Idempotency Rules

1. Read `lib/idempotency.md` before executing any step on a machine that may already have Rakkib resources.
2. Existing `.env` files are authoritative for secrets. Render a candidate file, merge in only missing keys, and never replace an existing secret value.
3. Render Caddy changes to a candidate file and validate before replacing the active Caddyfile. Restore the previous file and stop if validation fails.
4. Replace cron entries by Rakkib marker comments rather than appending new lines.
5. Detect existing Cloudflare tunnels by name before creating a new tunnel.
6. Use `./scripts/rakkib-doctor` as a standalone diagnostic and as the final Step 00 install gate.

## Privilege Rules

1. Linux orchestration is user-first. The bootstrapper should be run as `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/Simplify/install.sh | bash`.
2. Do not run the full AI agent session as root by default. If Rakkib is run as root, it must warn and ask the user to confirm before continuing.
3. In Phase 1 on Linux, check `id -u`. If it is not `0`, record `privilege_mode: sudo` and `privilege_strategy: on_demand`; continue the interview unprivileged.
4. If `id -u` is `0`, record `privilege_mode: root` and `privilege_strategy: root_process`, but warn the user that root orchestration is intended only for repair/debug sessions. If `SUDO_USER` is set, ask whether to restart as that admin user before continuing.
5. Do not try `sudo -S`, do not ask for passwords in chat, and do not store sudo credentials in `.fss-state.yaml`. If the user wants to pre-authorize sudo, ask them to run `rakkib auth sudo` in the terminal before confirmed privileged work starts.
6. After Phase 6 confirmation, privileged Linux actions should use `sudo -n` or `sudo -n rakkib privileged <allowlisted-action>` after briefly explaining what system area will change. If sudo authorization has expired, stop and ask the user to run `rakkib auth sudo`; do not hang on an interactive password prompt inside the agent session. Prefer `rakkib privileged` helpers when they exist.
7. Use `{{ADMIN_USER}}` as the owner for the repo, `/srv` files that should be user-writable, and user-scoped services. Step 90 must verify ownership for later unprivileged maintenance.
8. Prefer user-scoped installs when they satisfy the requirement. The host `cloudflared` CLI should be installed into the admin user's `~/.local/bin`.

## Platform Rules

Linux defaults:
- `data_root: /srv`
- init system: `systemd`
- `host_gateway: 172.18.0.1`
- detect LAN IP from the first non-loopback IPv4 returned by `hostname -I`

Mac defaults:
- `data_root: $HOME/srv`
- init system: `launchd`
- `host_gateway: host.docker.internal`
- detect LAN IP from an active interface such as `en0`

## Completion Rules

The deployment is complete only when:

1. The final `steps/90-verify.md` checks pass.
2. `{{DATA_ROOT}}/README.md` has been generated on the target machine.
3. `~/.claude/CLAUDE.md` has been created or updated with the Rakkib block delimited by `<!-- RAKKIB START -->` and `<!-- RAKKIB END -->`.
4. If `~/.config/github-copilot/AGENTS.md` or `~/.codex/AGENTS.md` already exist, the same Rakkib block has been synced into them.
5. The selected services are reachable on their expected domains.
6. The selected host addons pass their final verification checks.
