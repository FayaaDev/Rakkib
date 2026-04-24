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
  ssh_hostname: ssh
secrets:
  mode: generate
confirmed: false
```

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
3. The appropriate agent memory file has been appended or created.
4. The selected services are reachable on their expected domains.
