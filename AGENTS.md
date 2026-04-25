# Rakkib

Clone this repo onto the machine you want to turn into a Rakkib-style personal server kit.

This repository is built for an AI coding agent to operate as the installer. It includes a thin `install.sh` bootstrapper, but not a one-shot shell installer. The bootstrapper may clone/update the repo, run doctor, and launch a supported agent CLI with the installer prompt; the agent should still interview the user, record answers in `.fss-state.yaml`, render the provided templates, and execute the step files in order.

## Agent Prompt

If you are an AI coding agent:

1. Read `AGENT_PROTOCOL.md` first.
2. Do not execute anything outside this repo until Phase 6 (`questions/06-confirm.md`) is complete.
3. Ask the question files in order and record answers into `.fss-state.yaml`.
4. After confirmation, execute `steps/*.md` in numeric order, skipping optional restore-test work unless explicitly requested.
5. Pass every `## Verify` block before moving forward.

## Fresh Machine Start

On a fresh machine:

1. Install `git` and your coding agent CLI.
2. Clone this repo and enter it:

Bootstrap option:

```bash
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash
```

By default, the bootstrapper launches a supported agent CLI. If multiple supported agents are installed, it asks which one to use; if only one is installed, it launches that one. Use `bash -s -- --print-prompt` to only print the prompt, or `bash -s -- --agent opencode` to force a specific agent.

Manual option:

```bash
git clone https://github.com/FayaaDev/Rakkib.git
cd Rakkib
```

3. If the bootstrapper did not auto-launch an agent, start your agent from the repo root.
4. Paste this prompt when using the manual path:

```text
Read README.md and AGENT_PROTOCOL.md first.

Use this repo as the installer.
Ask me the question files in order.
Record answers in .fss-state.yaml.
Do not write outside the repo until Phase 6 (questions/06-confirm.md).
Use the helper-first Linux privilege flow instead of raw sudo for normal step execution.
After confirmation, execute steps/00-prereqs.md through steps/90-verify.md in numeric order, skipping optional restore-test work unless explicitly requested.
Stop on any failed Verify block and fix it before continuing.
```

Expected flow:

1. The agent asks `questions/01-platform.md` through `questions/06-confirm.md`.
2. On fresh Ubuntu Linux installs, the agent should prefer a preinstalled helper or install it during one bootstrap trust event in Step 00, then use the helper for later root-required work.
3. After confirmation, the agent runs the deployment steps in numeric order, including Step 05 preflight.
4. The run is complete only when `steps/90-verify.md` passes.
5. Record the run outcome in `DRY_RUN_REPORT.md` before calling the repo ready for outside users.

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
7. Run `steps/00-prereqs.md` through `steps/90-verify.md` in numeric order, skipping optional restore-test work unless explicitly requested

## Files

- `AGENT_PROTOCOL.md`: exact operating rules for the installer agent
- `registry.yaml`: service catalog and defaults
- `lib/placeholders.md`: canonical placeholder list
- `lib/validation.md`: reusable validation checklist
- `templates/`: rendered into target-machine configs
- `docs/`: reference material from the live Rakkib reference server

## State File

Use `.fss-state.yaml` as the only scratch state file during the interview and render phases. It is gitignored.

Derived defaults that must be recorded before rendering:

- `privilege_mode: sudo | root | none` on Linux, `sudo` on Mac
- `privilege_strategy: helper | root_process | none`
- `helper.installed: true | false`
- `helper.version: <number>|null`
- `helper.bootstrap_required: true | false`
- `claw_gateway_port: 18789`
- `cloudflared_metrics_port: 20241`
- `cloudflare.auth_method: browser_login | api_token | existing_tunnel`
- `cloudflare.headless: true | false | null`
- when `cloudflare.tunnel_uuid` is known:
  - `cloudflare.tunnel_creds_host_path: {{DATA_ROOT}}/data/cloudflared/<tunnel_uuid>.json`
  - `cloudflare.tunnel_creds_container_path: /home/nonroot/.cloudflared/<tunnel_uuid>.json`

## Agent Memory Outputs

Always write these targets on the target machine during `steps/90-verify.md`:

- `{{DATA_ROOT}}/README.md`
- `~/.claude/CLAUDE.md`

If present, also sync the same marked Rakkib block into:

- `~/.config/github-copilot/AGENTS.md`
- `~/.codex/AGENTS.md`

Use these markers to replace or append exactly one managed block:

```md
<!-- RAKKIB START -->
...
<!-- RAKKIB END -->
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

## Linux Privileges

- Fresh Ubuntu Linux installs need a privileged account for Docker Engine installation and some service setup.
- The standard Linux privilege path is a root-owned helper at `/usr/local/libexec/rakkib-root-helper` with a scoped `/etc/sudoers.d/rakkib-helper` rule for that path only.
- If the helper is not already present, Step 00 may use one bootstrap trust event to run `sudo ./scripts/install-privileged-helper --admin-user <user>`, but raw `sudo` is not the normal step execution model.
- The reviewed Ubuntu Docker helper path may install `acl` so it can bridge same-session Docker socket access without asking the user to run extra package installs by hand.
- Do not require the user to hand-edit `/etc/sudoers` or grant blanket `NOPASSWD` access.
- The host `cloudflared` CLI should be installed without root into `~/.local/bin/cloudflared` when it is missing.
