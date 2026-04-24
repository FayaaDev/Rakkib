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

## Success Condition

On a fresh machine, an agent should be able to use only this repo plus the user's answers to bring up:

- `https://{{NOCODB_SUBDOMAIN}}.<domain>`
- optional `https://{{N8N_SUBDOMAIN}}.<domain>`
- optional `https://{{DBHUB_SUBDOMAIN}}.<domain>`
- optional `https://{{OPENCLAW_SUBDOMAIN}}.<domain>`

with Caddy, Cloudflare Tunnel, and PostgreSQL configured in the same operating style as the source server.
