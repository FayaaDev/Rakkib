# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

Rakkib is an **AI-agent-driven server installer** — not a shell script. The agent interviews the user, records answers in `.fss-state.yaml`, renders templates, and executes step files in order. There is no one-shot installer to run directly.

The canonical operator prompt (paste this to kick off an install):

```text
Read README.md and AGENT_PROTOCOL.md first, then use this repo as the installer:
ask the question files in order, record answers in `.fss-state.yaml`, auto-detect
host values when instructed, do not write outside the repo until Phase 6
(`questions/06-confirm.md`), run as the normal admin user and request sudo only
for specific privileged setup actions after confirmation, then execute
`steps/00-prereqs.md` through `steps/90-verify.md` in numeric order and stop on any
failed `## Verify` block until it is fixed.
```

## Architecture

### Flow

```
questions/01-06 → .fss-state.yaml → steps/00-90 → target machine
```

1. **Interview phase** (`questions/01-platform.md` → `questions/06-confirm.md`): collect user answers into `.fss-state.yaml`, including `foundation_services`, `selected_services`, and per-service subdomains. No writes outside the repo until `confirmed: true`.
2. **Execution phase** (`steps/00-prereqs.md` → `steps/90-verify.md`): each step has an `## Inputs`, `## Actions`, and `## Verify` section. Agent must pass every `## Verify` block before advancing.

### Key Files

| File | Role |
|------|------|
| `AGENT_PROTOCOL.md` | Exact operating rules — read this before acting |
| `registry.yaml` | Service catalog with image, port, env keys, and optional flags |
| `lib/placeholders.md` | Canonical list of every `{{PLACEHOLDER}}` used in templates |
| `lib/validation.md` | Reusable validation checklist |
| `.fss-state.yaml` | Runtime state (gitignored) — single source of truth during install |

### Templates

All templates use `{{PLACEHOLDER}}` syntax — direct string substitution only. No separate templating tool. Before rendering any template, flatten `.fss-state.yaml` into the placeholder map defined in `lib/placeholders.md`. Do not leave unresolved placeholders in output files.

Platform-specific templates exist for `systemd` (Linux) and `launchd` (Mac) under `templates/`.

### Services

Always installed: **Caddy**, **Cloudflared**, **PostgreSQL** (`pgvector/pgvector:pg16`).

Foundation bundle (preselected, user may deselect): **NocoDB**, **Authentik**, **Homepage**, **Uptime Kuma**, **Dockge**.

Optional (user-selected): **n8n**, **DBHub**, **Immich** (CPU-only Docker stack with dedicated Postgres/Valkey), **OpenClaw** (host service, not a container).

Only render templates, compose files, blueprints, and public routes for services that remain selected.

## Privilege Model (Linux)

Linux installs use unprivileged orchestration with explicit sudo for system changes.

- **Canonical install path:** Run `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash`.
- **Local clone path:** From an existing clone, run `bash install.sh`.
- Phase 1 should record `privilege_mode: sudo` and `privilege_strategy: on_demand` for the normal user-first flow. Do not fall back to `sudo -S` or password-in-chat.
- If the agent is running as root, warn that root orchestration is intended only for repair/debug sessions. If `SUDO_USER` is available, prefer restarting as that user.
- Before agent launch, `rakkib init` may pre-authorize sudo and keep the sudo timestamp alive for the session. After confirmation, Linux root-required work should use `sudo -n` or allowlisted `sudo -n rakkib privileged ...` helper actions so expired authorization fails fast instead of prompting inside the agent session.
- Step 90 verifies repo and state-file ownership for later unprivileged maintenance.
- `cloudflared` CLI installs into the admin user's `~/.local/bin/cloudflared`.
- OpenClaw installs from npm into `~/.local/bin/openclaw` (requires node ≥ 22.14.0).

## State File

`.fss-state.yaml` must stay plain key/value (easy to diff, easy to hand-edit). Required derived values and service selections to record before rendering:

- `arch` — normalize to `amd64` or `arm64` (from `uname -m`)
- `lan_ip` — first non-loopback IPv4 (from `hostname -I` on Linux)
- `privilege_mode`, `privilege_strategy`
- `foundation_services` — kept from the recommended foundation bundle
- `selected_services` — optional add-on services the user chose
- foundation subdomains for selected services: `subdomains.nocodb`, `subdomains.auth`, `subdomains.home`, `subdomains.status`, `subdomains.dockge`
- optional subdomains for selected services: `subdomains.n8n`, `subdomains.dbhub`, `subdomains.immich`, `subdomains.claw`
- `claw_gateway_port: 18789`, `cloudflared_metrics_port: 20241` (always these defaults)
- `cloudflare.auth_method` — prefer `browser_login`; do not store raw Cloudflare API tokens in state
- `cloudflare.tunnel_creds_host_path` and `cloudflare.tunnel_creds_container_path` — derive from `tunnel_uuid` once known

## Critical Rules

- **Never rotate `N8N_ENCRYPTION_KEY`** after first run.
- **Never rotate `AUTHENTIK_SECRET_KEY`** after first run.
- Do not write outside the repo until `questions/06-confirm.md` sets `confirmed: true`.
- Stop on any failed `## Verify` block; fix before advancing.
- Preserve existing secrets when a file already exists on the target machine.
- If `cloudflare.zone_in_cloudflare` is `false`, do not mark the deploy successful until DNS and HTTPS are verified.

## Agent Memory Outputs (Step 90)

After a successful install, write:
- `{{DATA_ROOT}}/README.md` (from `templates/agent-memory/SERVER_README.md.tmpl`)
- `~/.claude/CLAUDE.md` (from `templates/agent-memory/CLAUDE.md.tmpl`)

Use `<!-- RAKKIB START -->` / `<!-- RAKKIB END -->` markers to manage the block. Sync the same block into `~/.config/github-copilot/AGENTS.md` and `~/.codex/AGENTS.md` if those files exist.

## Extending the Repo

- Add a new service: entry in `registry.yaml` + any new placeholders in `lib/placeholders.md` + service selection updates in `questions/03-services.md` + a new step in `steps/` if needed.
- Add a new template: register all `{{PLACEHOLDERS}}` it introduces in `lib/placeholders.md` in the same change.

## v1 Scope

Out of scope for v1: Google Drive backups, OpenCode host service, ChangeDetection, SehaRadar, LightRAG, Superset, Excalidraw. See `v2.md` for planned future CLI architecture.
