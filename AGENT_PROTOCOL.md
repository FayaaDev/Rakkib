# Agent Protocol

This file defines the exact operating procedure for any coding agent using this repository as an installer.

## Global Rules

1. Read `README.md`, `registry.yaml`, `lib/placeholders.md`, and the current question file before acting.
2. Use `.fss-state.yaml` as the single source of truth for collected answers and derived values.
3. Do not write outside the repo during Phases 1 through 6.
4. Ask questions exactly in order. Validate and normalize answers before recording them.
5. Do not skip required phases even if values seem obvious.
6. After confirmation, execute the step files in numeric order.
7. Stop on any failed `## Verify` block. Fix the issue before advancing.
8. Prefer minimal edits on the target machine. Preserve any existing user data or secrets unless explicitly replacing them.
9. Never rotate an existing `N8N_ENCRYPTION_KEY`.

## State File Shape

Maintain `.fss-state.yaml` with plain key/value data only. Keep it easy to diff and easy to edit by hand.

Expected high-level sections:

```yaml
platform: linux
arch: amd64
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
selected_services: [n8n]
subdomains:
  nocodb: nocodb
  n8n: n8n
cloudflare:
  zone_in_cloudflare: true
  tunnel_strategy: new
  tunnel_name: myserver
  ssh_subdomain: ssh
  tunnel_uuid: null
  tunnel_creds_host_path: null
  tunnel_creds_container_path: null
claw_gateway_port: 18789
cloudflared_metrics_port: 20241
secrets:
  mode: generate
confirmed: false
```

Derived value rules:

- Always derive `claw_gateway_port` as `18789` unless the repo is explicitly changed to ask for a different value.
- Always derive `cloudflared_metrics_port` as `20241` unless the repo is explicitly changed to ask for a different value.
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
- `cloudflared_metrics_port` -> `{{CLOUDFLARED_METRICS_PORT}}`

Nested mappings:

- `cloudflare.tunnel_uuid` -> `{{TUNNEL_UUID}}`
- `cloudflare.ssh_subdomain` -> `{{SSH_SUBDOMAIN}}`
- `cloudflare.tunnel_creds_host_path` -> `{{TUNNEL_CREDS_HOST_PATH}}`
- `cloudflare.tunnel_creds_container_path` -> `{{TUNNEL_CREDS_CONTAINER_PATH}}`
- `subdomains.nocodb` -> `{{NOCODB_SUBDOMAIN}}`
- if `n8n` is selected: `subdomains.n8n` -> `{{N8N_SUBDOMAIN}}`
- if `dbhub` is selected: `subdomains.dbhub` -> `{{DBHUB_SUBDOMAIN}}`
- if `openclaw` is selected: `subdomains.claw` -> `{{OPENCLAW_SUBDOMAIN}}`

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
  - `- OpenClaw at https://{{OPENCLAW_SUBDOMAIN}}.{{DOMAIN}}`

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
Run `questions/03-services.md`.

### Phase 4
Run `questions/04-cloudflare.md`.

### Phase 5
Run `questions/05-secrets.md`.

### Phase 6
Run `questions/06-confirm.md`.

Only after `confirmed: true` may the agent modify the target machine.

## Execution Order

After confirmation, run these step files in order:

1. `steps/00-prereqs.md`
2. `steps/10-layout.md`
3. `steps/20-network.md`
4. `steps/30-caddy.md`
5. `steps/40-cloudflare.md`
6. `steps/50-postgres.md`
7. `steps/60-services.md`
8. `steps/70-host-agents.md`
9. `steps/80-backups.md`
10. `steps/85-health-crons.md`
11. `steps/90-verify.md`

## Rendering Rules

1. Render by direct placeholder substitution only.
2. Do not introduce a separate templating tool unless the user asks.
3. Render only the files required by the selected services.
4. Keep generated secrets out of git-tracked files outside `.fss-state.yaml`.
5. When a file already exists on the target machine, read it first and preserve any values that must not rotate.
6. For Cloudflared, always normalize the credentials JSON to `{{DATA_ROOT}}/data/cloudflared/<tunnel_uuid>.json` on the host and render the in-container path `/home/nonroot/.cloudflared/<tunnel_uuid>.json` into `config.yml`.
7. For SSH over Cloudflare, always use the recorded custom subdomain value rather than assuming `ssh`.
8. A local host `cloudflared` CLI is required for tunnel login, creation, and DNS routing. The container image alone is not enough for Step 40.
9. If `secrets.mode` is `generate`, generate each missing secret immediately before the first step that needs it, then write it back into `.fss-state.yaml` before rendering any file that uses it.

## Platform Rules

Linux defaults:
- `data_root: /srv`
- init system: `systemd`
- `host_gateway: 172.18.0.1`

Mac defaults:
- `data_root: $HOME/srv`
- init system: `launchd`
- `host_gateway: host.docker.internal`

## Completion Rules

The deployment is complete only when:

1. The final `steps/90-verify.md` checks pass.
2. `{{DATA_ROOT}}/README.md` has been generated on the target machine.
3. `~/.claude/CLAUDE.md` has been created or updated with the FayaaSRV block delimited by `<!-- FAYAASRV START -->` and `<!-- FAYAASRV END -->`.
4. If `~/.config/github-copilot/AGENTS.md` or `~/.codex/AGENTS.md` already exist, the same FayaaSRV block has been synced into them.
5. The selected services are reachable on their expected domains.
