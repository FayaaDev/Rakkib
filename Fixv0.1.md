# Fix v0.1

This file captures the blocking issues found in the current `FayaaSRV` repo and the concrete fixes needed before calling the repo ready for outside users.

## Current Status

Repo status after the current doc/template fixes:

- Items 1 through 7 are addressed in-repo.
- Item 8 remains a release gate that requires real clean-machine dry runs and recorded passing results in `DRY_RUN_REPORT.md`.

## Goal

Make the repo usable by a fresh agent on a fresh machine without hidden assumptions, unresolved placeholders, or broken path mismatches.

## 1. Fix Cloudflared Credentials Path Handling

### Problem

The interview and step docs treat the tunnel credentials file path as a host path, but the rendered `config.yml` is consumed inside the `cloudflared` container.

Current mismatch:

- `questions/04-cloudflare.md` asks for the credentials file path on the machine.
- `templates/cloudflared/config.yml.tmpl` writes that path directly to `credentials-file`.
- `templates/docker/cloudflared/docker-compose.yml.tmpl` mounts `{{DATA_ROOT}}/data/cloudflared` at `/home/nonroot/.cloudflared` inside the container.

Result: a host path like `/srv/data/cloudflared/credentials.json` will not exist inside the container.

### Fix

Choose one consistent model and document it everywhere.

Recommended model:

1. Store the credentials file on the host at `{{DATA_ROOT}}/data/cloudflared/<tunnel_uuid>.json`.
2. Always mount that directory to `/home/nonroot/.cloudflared` in the container.
3. Render `credentials-file` inside `config.yml` as the in-container path:
   `/home/nonroot/.cloudflared/<tunnel_uuid>.json`
4. In `.fss-state.yaml`, distinguish between:
   - `tunnel_creds_host_path`
   - `tunnel_creds_container_path`

### Files to update

- `questions/04-cloudflare.md`
- `AGENT_PROTOCOL.md`
- `steps/40-cloudflare.md`
- `templates/cloudflared/config.yml.tmpl`
- `lib/placeholders.md`
- `lib/validation.md`

## 2. Honor Custom SSH Hostname

### Problem

The user can choose a custom SSH hostname, but the template is hardcoded to `ssh.{{DOMAIN}}`.

### Fix

1. Add a dedicated placeholder such as `{{SSH_SUBDOMAIN}}` or `{{CF_SSH_SUBDOMAIN}}`.
2. Record it in `.fss-state.yaml` during phase 4.
3. Use that placeholder in:
   - `templates/cloudflared/config.yml.tmpl`
   - `steps/40-cloudflare.md`
   - `lib/placeholders.md`
4. Update verification and docs to reference the same value.

### Files to update

- `questions/04-cloudflare.md`
- `AGENT_PROTOCOL.md`
- `templates/cloudflared/config.yml.tmpl`
- `steps/40-cloudflare.md`
- `lib/placeholders.md`

## 3. Align OpenClaw Service Names

### Problem

The installed Linux unit is `openclaw-gateway.service`, but the health scripts monitor `claw-gateway.service`.

### Fix

Standardize on one service name.

Recommended value:

- `openclaw-gateway.service`

Update every health script, step file, and validation reference to use the same unit name.

### Files to update

- `steps/70-host-agents.md`
- `steps/85-health-crons.md`
- `lib/validation.md`
- `templates/backups/healthchecks/claw-healthcheck.sh.tmpl`
- `templates/backups/healthchecks/claw-memory-alert.sh.tmpl`
- `templates/systemd/claw-gateway.service.tmpl`

## 4. Make OpenClaw Actually Installable

### Problem

The repo currently installs only service wrappers. It assumes OpenClaw is already installed globally.

Current assumptions:

- Linux: `/usr/lib/node_modules/openclaw/dist/index.js` already exists.
- Mac: `openclaw` already exists on `PATH`.

That makes the repo unusable on a clean machine for users who select OpenClaw.

### Fix

Define and document one supported install path for OpenClaw.

Recommended options:

1. Preferred: install OpenClaw from npm or another canonical package source during `steps/70-host-agents.md`.
2. Alternate: mark OpenClaw as experimental and remove it from v1 until the install path is stable.

If keeping OpenClaw in v1:

1. Add installation commands for Linux and Mac.
2. Add verification that the binary or entrypoint exists before writing the service file.
3. Use a service template that depends on a real installed binary path.
4. Add rollback/debug guidance if install fails.

### Files to update

- `steps/70-host-agents.md`
- `registry.yaml`
- `templates/systemd/claw-gateway.service.tmpl`
- `templates/launchd/claw-gateway.plist.tmpl`
- `README.md`
- `AGENTS.md`

## 5. Define All Required Derived Placeholders

### Problem

Some placeholders used by templates are documented but never collected or derived in the interview flow.

Current risky placeholders:

- `{{CLAW_GATEWAY_PORT}}`
- `{{CLOUDFLARED_METRICS_PORT}}`
- `{{OPENCLAW_VERSION}}`

An agent may leave these unresolved or invent values.

### Fix

Every placeholder must be either:

1. directly collected from the user,
2. deterministically derived in the protocol, or
3. removed from active templates.

Recommended defaults:

- `claw_gateway_port: 18789`
- `cloudflared_metrics_port: 20241`
- `openclaw_version: latest` only if still needed

If `OPENCLAW_VERSION` is only decorative, remove it from templates entirely.

### Files to update

- `AGENT_PROTOCOL.md`
- `questions/*.md` if asking is needed
- `lib/placeholders.md`
- `templates/systemd/claw-gateway.service.tmpl`
- `templates/backups/healthchecks/cloudflared-healthcheck.sh.tmpl`

## 6. Specify Agent-Memory Output Paths

### Problem

The repo says to create or append a local agent memory file, but does not define the actual target paths in the execution step.

That leaves room for agent inconsistency.

### Fix

Define explicit target paths.

Recommended behavior:

1. Always generate `{{DATA_ROOT}}/README.md`.
2. Append or create:
   - `~/.claude/CLAUDE.md`
3. Optionally also update, if present:
   - `~/.config/github-copilot/AGENTS.md`
   - `~/.codex/AGENTS.md`

Also define the exact append marker to avoid duplicate insertions.

Suggested marker:

```md
<!-- FAYAASRV START -->
...
<!-- FAYAASRV END -->
```

### Files to update

- `steps/90-verify.md`
- `AGENT_PROTOCOL.md`
- `README.md`
- `AGENTS.md`
- `templates/agent-memory/CLAUDE.md.tmpl`

## 7. Sync Registry Metadata With Templates

### Problem

`registry.yaml` still describes n8n as a custom image build, but the template now uses `n8nio/n8n:latest`.

### Fix

Update `registry.yaml` so it matches the actual deployment templates.

### Files to update

- `registry.yaml`

## 8. Dry-Run Requirement Before External Use

### Problem

The repo has not yet proven a complete clean-machine install loop.

### Fix

Before calling the repo ready for other users:

1. Run one fresh Ubuntu 24.04 dry-run for the baseline stack:
   - Caddy
   - Cloudflared
   - PostgreSQL
   - NocoDB
2. Run one dry-run with optional `n8n` and `dbhub` enabled.
3. If OpenClaw remains in v1, run one dry-run with OpenClaw enabled.
4. Record observed gaps in a short test report.

### Suggested artifact

Add a file such as `DRY_RUN_REPORT.md` with:

- platform
- selected services
- result
- blockers found
- fixes applied

## Release Gate

Do not call `FayaaSRV` ready for outside users until all of the following are true:

1. Cloudflared credentials path handling is internally consistent.
2. Custom SSH hostname is respected end to end.
3. OpenClaw either installs correctly on a clean machine or is removed from v1.
4. All active placeholders have clear sources or defaults.
5. Agent-memory output paths are explicit.
6. `registry.yaml` matches the live templates.
7. At least one clean-machine dry-run passes `steps/90-verify.md`.
