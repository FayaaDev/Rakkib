# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

Rakkib is an **AI-agent-driven server installer** — not a shell script. The agent interviews the user, records answers in `.fss-state.yaml`, renders templates, and executes step files in order. There is no one-shot installer to run directly.

The canonical operator prompt (paste this to kick off an install):

```text
Read README.md and AGENT_PROTOCOL.md first, then use this repo as the installer:
ask the question files in order, record answers in `.fss-state.yaml`, auto-detect
host values when instructed, do not write outside the repo until Phase 6
(`questions/06-confirm.md`), use the helper-first Linux privilege flow instead of
raw sudo for normal step execution, then after confirmation execute
`steps/00-prereqs.md` through `steps/90-verify.md` in numeric order and stop on any
failed `## Verify` block until it is fixed.
```

## Architecture

### Flow

```
questions/01-06 → .fss-state.yaml → steps/00-90 → target machine
```

1. **Interview phase** (`questions/01-platform.md` → `questions/06-confirm.md`): collect user answers into `.fss-state.yaml`. No writes outside the repo until `confirmed: true`.
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

Always installed: **Caddy**, **Cloudflared**, **PostgreSQL** (`pgvector/pgvector:pg16`), **NocoDB**.

Optional (user-selected): **n8n**, **DBHub**, **OpenClaw** (host service, not a container).

Only render templates and write compose files for selected services.

## Privilege Model (Linux)

The standard path is a root-owned helper at `/usr/local/libexec/rakkib-root-helper` with a scoped `sudoers.d` rule for that path only.

- Helper present → `privilege_strategy: helper`; route all root work through helper verbs.
- Helper absent + `privilege_mode: sudo` → one bootstrap trust event: `sudo ./scripts/install-privileged-helper --admin-user <user>`, then verify with `sudo -n /usr/local/libexec/rakkib-root-helper probe`.
- After bootstrap, **do not use raw `sudo`** in later steps. Introduce a new reviewed helper verb instead.
- `cloudflared` CLI installs without root into `~/.local/bin/cloudflared`.
- OpenClaw installs from npm into `~/.local/bin/openclaw` (requires node ≥ 22.14.0).

## State File

`.fss-state.yaml` must stay plain key/value (easy to diff, easy to hand-edit). Required derived values to record before rendering:

- `arch` — normalize to `amd64` or `arm64` (from `uname -m`)
- `lan_ip` — first non-loopback IPv4 (from `hostname -I` on Linux)
- `privilege_mode`, `privilege_strategy`, `helper.*`
- `claw_gateway_port: 18789`, `cloudflared_metrics_port: 20241` (always these defaults)
- `cloudflare.auth_method` — prefer `browser_login`; do not store raw Cloudflare API tokens in state
- `cloudflare.tunnel_creds_host_path` and `cloudflare.tunnel_creds_container_path` — derive from `tunnel_uuid` once known

## Critical Rules

- **Never rotate `N8N_ENCRYPTION_KEY`** after first run.
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

- Add a new service: entry in `registry.yaml` + any new placeholders in `lib/placeholders.md` + a new step in `steps/` if needed.
- Add a new template: register all `{{PLACEHOLDERS}}` it introduces in `lib/placeholders.md` in the same change.

## v1 Scope

Out of scope for v1: Google Drive backups, OpenCode host service, ChangeDetection, SehaRadar, LightRAG, Superset, Excalidraw. See `v2.md` for planned future CLI architecture.
