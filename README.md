# FayaaSRV

Clone this repo onto the machine you want to turn into a Fayaa-style personal server kit.

This repository is built for an AI coding agent to operate as the installer. It does not include a one-shot shell installer. The agent should interview the user, record answers in `.fss-state.yaml`, render the provided templates, and execute the step files in order.

## Agent Prompt

If you are an AI coding agent:

1. Read `AGENT_PROTOCOL.md` first.
2. Do not execute anything outside this repo until Phase 6 (`questions/06-confirm.md`) is complete.
3. Ask the question files in order and record answers into `.fss-state.yaml`.
4. After confirmation, execute `steps/*.md` in order.
5. Pass every `## Verify` block before moving forward.

## v1 Scope

Always install:
- Caddy
- Cloudflared
- PostgreSQL
- NocoDB

Optional per user choice:
- n8n
- DBHub
- OpenClaw

OpenClaw install model in v1:
- When selected, install OpenClaw from npm as a user-scoped binary at `~/.local/bin/openclaw`.
- Require `node >= 22.14.0` and `npm` before rendering the host service wrapper.

Out of scope for v1:
- Google Drive / rclone backups
- OpenCode host service
- ChangeDetection, SehaRadar, LightRAG, Superset, Excalidraw
- Example apps from the reference server

## Flow

1. Ask `questions/01-platform.md`
2. Ask `questions/02-identity.md`
3. Ask `questions/03-services.md`
4. Ask `questions/04-cloudflare.md`
5. Ask `questions/05-secrets.md`
6. Ask `questions/06-confirm.md`
7. Run `steps/00-prereqs.md` through `steps/90-verify.md`

## Files

- `AGENT_PROTOCOL.md`: exact operating rules for the installer agent
- `registry.yaml`: service catalog and defaults
- `lib/placeholders.md`: canonical placeholder list
- `lib/validation.md`: reusable validation checklist
- `templates/`: rendered into target-machine configs
- `docs/`: reference material from the live FayaaLink server

## State File

Use `.fss-state.yaml` as the only scratch state file during the interview and render phases. It is gitignored.

Derived defaults that must be recorded before rendering:

- `claw_gateway_port: 18789`
- `cloudflared_metrics_port: 20241`
- when `cloudflare.tunnel_uuid` is known:
  - `cloudflare.tunnel_creds_host_path: {{DATA_ROOT}}/data/cloudflared/<tunnel_uuid>.json`
  - `cloudflare.tunnel_creds_container_path: /home/nonroot/.cloudflared/<tunnel_uuid>.json`

## Agent Memory Outputs

Always write these targets on the target machine during `steps/90-verify.md`:

- `{{DATA_ROOT}}/README.md`
- `~/.claude/CLAUDE.md`

If present, also sync the same marked FayaaSRV block into:

- `~/.config/github-copilot/AGENTS.md`
- `~/.codex/AGENTS.md`

Use these markers to replace or append exactly one managed block:

```md
<!-- FAYAASRV START -->
...
<!-- FAYAASRV END -->
```

## Dry Run Report

Record clean-machine validation runs in `DRY_RUN_REPORT.md` before calling the repo ready for outside users.

Do not call the repo public-ready until the required clean-machine runs are recorded there as passing.

## Success Condition

On a fresh machine, an agent should be able to use only this repo plus the user's answers to bring up:

- `https://{{NOCODB_SUBDOMAIN}}.<domain>`
- optional `https://{{N8N_SUBDOMAIN}}.<domain>`
- optional `https://{{DBHUB_SUBDOMAIN}}.<domain>`
- optional `https://{{OPENCLAW_SUBDOMAIN}}.<domain>`

with Caddy, Cloudflare Tunnel, and PostgreSQL configured in the same operating style as the source server.
