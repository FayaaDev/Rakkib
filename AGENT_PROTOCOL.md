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

## AgentSchema Contract

Question files may layer a machine-readable schema into the markdown with a single fenced `yaml` block under a `## AgentSchema` heading. `lib/question-schema.md` is the compact reference for that embedded shape.

Keep the schema small and explicit. The current v1 question files use a compact metadata layout with phase-level keys such as `reads_state`, `writes_state`, and `fields`, plus a small number of phase-specific sections like `service_catalog`, `rules`, and `execution_generated_only` where needed.

Within those blocks, record canonical state keys and canonical enum, service, and host-addon values only. The normalized per-phase contract below remains authoritative for prompts, defaults, validation, derived values, and cross-phase dependencies.

Canonical answer normalization:

- `bool` questions accept `y`, `yes`, `true`, `n`, `no`, and `false`, and normalize to `true` or `false`.
- `platform` accepts `linux`, `mac`, `macos`, `osx`, and `darwin`, and normalizes to `linux` or `mac`.
- `cloudflare.tunnel_strategy` accepts `new`, `existing`, and `reuse`, and normalizes to `new` or `existing`.
- `secrets.n8n_mode` accepts `fresh`, `migrate`, `restore`, and `restoring`, and normalizes to `fresh` or `migrate`.
- Service answers must record canonical service slugs only: `nocodb`, `authentik`, `homepage`, `uptime-kuma`, `dockge`, `n8n`, `dbhub`, `immich`, `transfer`, `openclaw`, `hermes`.
- Host addon answers must record canonical addon slugs only: `vergo_terminal`.

Authoritative question contract:

```yaml
schema_version: 1
phases:
  - phase: 1
    file: questions/01-platform.md
    state_dependencies: []
    host_detect:
      - key: arch
        command: uname -m
        normalize:
          x86_64: amd64
          aarch64: arm64
          arm64: arm64
      - key: privilege_mode
        when: platform == linux
        command: id -u
        derive:
          "0":
            privilege_mode: root
            privilege_strategy: root_process
          default:
            privilege_mode: sudo
            privilege_strategy: on_demand
      - key: privilege_mode
        when: platform == mac
        derive:
          default:
            privilege_mode: sudo
            privilege_strategy: on_demand
      - key: host_gateway
        derive:
          linux: 172.18.0.1
          mac: host.docker.internal
    questions:
      - key: platform
        type: enum
        prompt: What platform are you installing on?
        required: true
        values: [linux, mac]
        aliases:
          linux: [linux]
          mac: [mac, macos, osx, darwin]
      - key: docker_installed
        type: bool
        prompt: Is Docker already installed and running on this machine? (y/n)
        required: true

  - phase: 2
    file: questions/02-identity.md
    state_dependencies: [platform]
    host_detect:
      - key: lan_ip
        when: platform == linux
        command: hostname -I
        derive: first_non_loopback_ipv4
      - key: lan_ip
        when: platform == mac
        command: ipconfig getifaddr en0
        derive: first_active_interface_ipv4
      - key: data_root
        derive:
          linux: /srv
          mac: $HOME/srv
      - key: docker_net
        derive: caddy_net
      - key: backup_dir
        derive_from: data_root
        template: "{{data_root}}/backups"
    questions:
      - key: server_name
        type: string
        prompt: What is your server name? (e.g. myserver — used in configs and backup manifests)
        required: true
        validate: ^[a-z0-9-]+$
      - key: domain
        type: string
        prompt: What is your base domain? (e.g. example.com — all services will be subdomains of this)
        required: true
        validate: domain_no_scheme
      - key: cloudflare.zone_in_cloudflare
        type: bool
        prompt: Is this base domain already managed in Cloudflare in the same account you will use for this server? (y/n)
        required: true
      - key: admin_user
        type: string
        prompt: What is the admin username on this machine? (e.g. ubuntu — used in file paths and service ownership)
        required: true
      - key: admin_email
        type: string
        prompt: What is the admin email address? (used for NocoDB admin account and service notifications)
        required: true
        validate: contains_at_sign
      - key: tz
        type: string
        prompt: What is your timezone in IANA format? (e.g. America/New_York, Europe/London, Asia/Riyadh, Asia/Tokyo, Australia/Sydney, UTC)
        required: true

  - phase: 3
    file: questions/03-services.md
    state_dependencies: [domain]
    questions:
      - key: foundation_services
        type: enum
        multi: true
        prompt: Foundation Bundle: type service slugs to deselect (e.g. `homepage dockge`); numeric aliases like `3 5` are also accepted, or press Enter to accept all:
        required: true
        values: [nocodb, authentik, homepage, uptime-kuma, dockge]
        default: [nocodb, authentik, homepage, uptime-kuma, dockge]
      - key: selected_services
        type: enum
        multi: true
        prompt: Optional Services: type service slugs to add (e.g. `n8n immich hermes`); numeric aliases like `6 8 11` are also accepted, or press Enter to skip all:
        required: true
        values: [n8n, dbhub, immich, transfer, openclaw, hermes]
        default: []
        depends_on:
          hermes:
            foundation_services: [authentik]
      - key: host_addons
        type: enum
        multi: true
        prompt: Optional Host Addons: type addon slugs to add (e.g. `vergo_terminal`); numeric aliases like `12` are also accepted, or press Enter to skip all:
        required: true
        values: [vergo_terminal]
        default: []
      - key: customize_subdomains
        type: bool
        prompt: Do you want to customize any subdomains? Defaults: nocodb, auth, home, status, dockge, n8n, dbhub, immich, transfer, claw, hermes. (y/n)
        required: true
      - key: subdomains
        type: host_detected
        required: true
        derive:
          nocodb: nocodb
          authentik: auth
          homepage: home
          uptime-kuma: status
          dockge: dockge
          n8n: n8n
          dbhub: dbhub
          immich: immich
          transfer: transfer
          openclaw: claw
          hermes: hermes
        writes:
          selected_service_subdomain_keys_only: true

  - phase: 4
    file: questions/04-cloudflare.md
    state_dependencies: [server_name, cloudflare.zone_in_cloudflare]
    questions:
      - key: cloudflare.tunnel_strategy
        type: enum
        prompt: Should Rakkib create a new Cloudflare tunnel for this server, or reuse an existing one? (new/existing)
        required: true
        values: [new, existing]
        aliases:
          new: [new]
          existing: [existing, reuse]
      - key: cloudflare.headless
        type: bool
        prompt: When Rakkib reaches Step 40, the install will pause while Cloudflare approves this server. Is this server headless, meaning it has no browser or desktop? (y/n)
        required: true
        when: cloudflare.tunnel_strategy == new
        writes:
          cloudflare.auth_method: browser_login
      - key: cloudflare.accept_browser_login
        type: bool
        prompt: Use this Cloudflare login method? (y/n)
        required: true
        when: cloudflare.tunnel_strategy == new
      - key: cloudflare.auth_method
        type: enum
        prompt: Do you need the advanced API token method for a headless or automated setup? (y/n)
        required: false
        when: cloudflare.tunnel_strategy == new && cloudflare.accept_browser_login == false
        values: [api_token]
        accepted_inputs:
          y: api_token
          yes: api_token
          n: stop
          no: stop
      - key: cloudflare.auth_method
        type: host_detected
        required: true
        when: cloudflare.tunnel_strategy == existing
        derive: existing_tunnel
      - key: cloudflare.tunnel_name
        type: string
        prompt: What tunnel name should be used? [default: <server_name>]
        required: true
        default_from: server_name
      - key: cloudflare.ssh_subdomain
        type: string
        prompt: What subdomain should route to SSH over Cloudflare? [default: ssh]
        required: true
        default: ssh
        validate: ^[a-z0-9-]+$
      - key: knows_tunnel_uuid
        type: bool
        prompt: Do you already know the existing tunnel UUID? (y/n)
        required: false
        when: cloudflare.tunnel_strategy == existing
      - key: cloudflare.tunnel_uuid
        type: string
        prompt: Existing tunnel UUID?
        required: false
        when: cloudflare.tunnel_strategy == existing && knows_tunnel_uuid == true
        validate: uuid

  - phase: 5
    file: questions/05-secrets.md
    state_dependencies: [foundation_services, selected_services]
    questions:
      - key: secrets.mode
        type: enum
        prompt: Do you want the agent to generate all required passwords and keys automatically? (y/n)
        required: true
        values: [generate, manual]
        aliases:
          generate: [y, yes, true]
          manual: [n, no, false]
      - key: secrets.n8n_mode
        type: enum
        prompt: Is this a fresh n8n install, or are you restoring/migrating an existing n8n instance? (fresh/migrate)
        required: false
        when: selected_services includes n8n
        values: [fresh, migrate]
        aliases:
          fresh: [fresh]
          migrate: [migrate, restore, restoring]
      - key: secrets.values
        type: host_detected
        required: true
        derive:
          required:
            - POSTGRES_PASSWORD
          if_foundation_services:
            nocodb: [NOCODB_DB_PASS, NOCODB_ADMIN_PASS]
            authentik: [AUTHENTIK_SECRET_KEY, AUTHENTIK_DB_PASS, AUTHENTIK_ADMIN_PASS]
          if_both_foundation_services:
            - services: [nocodb, authentik]
              keys: [NOCODB_OIDC_CLIENT_ID, NOCODB_OIDC_CLIENT_SECRET]
          if_selected_services:
            n8n: [N8N_DB_PASS, N8N_ENCRYPTION_KEY]
            immich: [IMMICH_DB_PASSWORD, IMMICH_VERSION]

  - phase: 6
    file: questions/06-confirm.md
    state_dependencies: [platform, arch, privilege_mode, privilege_strategy, server_name, domain, admin_user, admin_email, lan_ip, tz, foundation_services, selected_services, host_addons, cloudflare, secrets]
    questions:
      - key: confirmed
        type: bool
        prompt: Proceed with deployment using the above configuration? (y/n)
        required: true
```

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
foundation_services: [nocodb, authentik, homepage, uptime-kuma, dockge]
host_addons: [vergo_terminal]
subdomains:
  nocodb: nocodb
  authentik: auth
  homepage: home
  uptime-kuma: status
  dockge: dockge
  n8n: n8n
  dbhub: dbhub
  immich: immich
  transfer: transfer
  openclaw: claw
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
  n8n_mode: fresh
  values:
    POSTGRES_PASSWORD: null
    NOCODB_DB_PASS: null
    NOCODB_ADMIN_PASS: null
    AUTHENTIK_SECRET_KEY: null
    AUTHENTIK_DB_PASS: null
    AUTHENTIK_ADMIN_PASS: null
    NOCODB_OIDC_CLIENT_ID: null
    NOCODB_OIDC_CLIENT_SECRET: null
    N8N_DB_PASS: null
    N8N_ENCRYPTION_KEY: null
    IMMICH_DB_PASSWORD: null
    IMMICH_VERSION: null
confirmed: false
```

Derived value rules:

- Detect `arch` from the host with `uname -m` during Phase 1 and normalize it to `amd64` or `arm64` before recording it.
- Detect `lan_ip` from the host during Phase 2 and record the first usable LAN IPv4 address before rendering templates.
- Derive `data_root` from `platform` as `/srv` on Linux and `$HOME/srv` on Mac.
- Derive `docker_net` as `caddy_net`.
- Derive `backup_dir` as `{{data_root}}/backups` after `data_root` is known.
- Derive `host_gateway` from `platform` as `172.18.0.1` on Linux and `host.docker.internal` on Mac.
- Always derive `claw_gateway_port` as `18789` unless the repo is explicitly changed to ask for a different value.
- Always derive `hermes_dashboard_port` as `9119` unless the repo is explicitly changed to ask for a different value.
- Always derive `cloudflared_metrics_port` as `20241` unless the repo is explicitly changed to ask for a different value.
- If `hermes` is selected, `authentik` must remain in `foundation_services`; do not expose the Hermes dashboard without Authentik protection in v1.
- `foundation_services` may contain only `nocodb`, `authentik`, `homepage`, `uptime-kuma`, and `dockge`.
- `selected_services` may contain only `n8n`, `dbhub`, `immich`, `transfer`, `openclaw`, and `hermes`.
- `host_addons` may contain only `vergo_terminal` in v1.
- Record Cloudflare auth as `cloudflare.auth_method` with one of `browser_login`, `api_token`, or `existing_tunnel`. Use `browser_login` as the normal path and record `cloudflare.headless` as `true` or `false` for new tunnels.
- On Linux, the installer orchestration should run as the normal admin user. Record `privilege_mode: sudo` and `privilege_strategy: on_demand` unless the user is intentionally repairing from a root shell.
- If Linux is running as root through `sudo` with `SUDO_USER` set, prefer re-running `rakkib init` as `SUDO_USER` before launching an agent. Do not run the full AI agent session as root by default.
- On Mac, record `privilege_mode: sudo` and `privilege_strategy: on_demand`.
- If `cloudflare.tunnel_strategy` is `existing`, derive `cloudflare.auth_method: existing_tunnel` and `cloudflare.headless: null` unless a repair path later requires browser login.
- When `cloudflare.tunnel_uuid` is known, derive and record:
  - `cloudflare.tunnel_creds_host_path: {{DATA_ROOT}}/data/cloudflared/<tunnel_uuid>.json`
  - `cloudflare.tunnel_creds_container_path: /home/nonroot/.cloudflared/<tunnel_uuid>.json`
- In `secrets.mode: generate`, keep missing values as `null` until the first step that needs them.
- If `immich` is selected, default `secrets.values.IMMICH_VERSION` to `release` before rendering Immich files unless the repo is explicitly changed to pin a different tag.
- In `secrets.mode: manual`, require explicit values only for the keys selected by the schema above.
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
- if `nocodb` is in `foundation_services`: `subdomains.nocodb` -> `{{NOCODB_SUBDOMAIN}}`
- if `authentik` is in `foundation_services`: `subdomains.authentik` -> `{{AUTHENTIK_SUBDOMAIN}}`
- if `homepage` is in `foundation_services`: `subdomains.homepage` -> `{{HOMEPAGE_SUBDOMAIN}}`
- if `uptime-kuma` is in `foundation_services`: `subdomains.uptime-kuma` -> `{{UPTIME_KUMA_SUBDOMAIN}}`
- if `dockge` is in `foundation_services`: `subdomains.dockge` -> `{{DOCKGE_SUBDOMAIN}}`
- if `n8n` is selected: `subdomains.n8n` -> `{{N8N_SUBDOMAIN}}`
- if `dbhub` is selected: `subdomains.dbhub` -> `{{DBHUB_SUBDOMAIN}}`
- if `immich` is selected: `subdomains.immich` -> `{{IMMICH_SUBDOMAIN}}`
- if `transfer` is selected: `subdomains.transfer` -> `{{TRANSFER_SUBDOMAIN}}`
- if `openclaw` is selected: `subdomains.openclaw` -> `{{OPENCLAW_SUBDOMAIN}}`
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
- Append foundation bundle lines only for selected foundation services:
  - `- NocoDB at https://{{NOCODB_SUBDOMAIN}}.{{DOMAIN}}`
  - `- Authentik at https://{{AUTHENTIK_SUBDOMAIN}}.{{DOMAIN}}`
  - `- Homepage at https://{{HOMEPAGE_SUBDOMAIN}}.{{DOMAIN}}`
  - `- Uptime Kuma at https://{{UPTIME_KUMA_SUBDOMAIN}}.{{DOMAIN}}`
  - `- Dockge at https://{{DOCKGE_SUBDOMAIN}}.{{DOMAIN}}`
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
11. For browser-login flows, standardize the Cloudflare auth cert at `{{DATA_ROOT}}/data/cloudflared/cert.pem` when possible. Treat it as a local runtime auth artifact, preserve it on re-runs, include it in backups, and do not record it in `.fss-state.yaml`.
12. For new tunnels using `browser_login`, authenticate successfully before tunnel discovery. Do not run `cloudflared tunnel list` or tunnel creation commands until the login handoff is complete and the correct Cloudflare account has approved `{{DOMAIN}}`.
13. If `cloudflare.auth_method` is `api_token`, request the token only during Step 40, use it as a temporary environment variable, and unset it after Cloudflare work is complete. Do not persist the raw token in `.fss-state.yaml`.
14. If `secrets.mode` is `generate`, generate each missing secret immediately before the first step that needs it, then write it back into `.fss-state.yaml` before rendering any file that uses it.
15. If `cloudflare.zone_in_cloudflare` is `false`, help the user complete Cloudflare zone setup using the official docs before treating public DNS routing or HTTPS verification as complete. Do not mark the deployment fully successful while Step 40 DNS routing or Step 90 public HTTPS checks are still blocked by missing Cloudflare zone ownership.

## Idempotency Rules

1. Read `lib/idempotency.md` before executing any step on a machine that may already have Rakkib resources.
2. Existing `.env` files are authoritative for secrets. Render a candidate file, merge in only missing keys, and never replace an existing secret value.
3. Render Caddy changes to a candidate file and validate before replacing the active Caddyfile. Restore the previous file and stop if validation fails.
4. Replace cron entries by Rakkib marker comments rather than appending new lines.
5. Detect existing Cloudflare tunnels by name before creating a new tunnel.
6. Use `rakkib doctor` as a standalone diagnostic and as the final Step 00 install gate.

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
