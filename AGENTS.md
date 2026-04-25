# Rakkib

Clone this repo onto the machine you want to turn into a Rakkib-style personal server kit.

This repository is built for an AI coding agent to operate as the installer. The thin remote `install.sh` bootstrapper clones/updates the repo, checks Linux root privileges, runs doctor, and launches a supported agent CLI with the installer prompt. The agent should still interview the user, record answers in `.fss-state.yaml`, render the provided templates, and execute the step files in order.

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
2. Run the bootstrapper:

```bash
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash
```

On Linux, this first attempt is allowed to fail fast with an explicit root rerun command. The canonical Linux command is:

```bash
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | sudo -E bash
```

By default, `install.sh`:
- Clones or updates this repo
- Stops on Linux unless it is running as root
- Runs the doctor diagnostic
- Launches a supported agent CLI with the installer prompt

If multiple supported agents are installed, it asks which one to use; if only one is installed, it launches that one. Use `sudo -E bash -s -- --print-prompt` to only print the prompt, or `sudo -E bash -s -- --agent opencode` to force a specific agent when using the curl pipe on Linux.

**Manual clone option** (if you prefer to clone first):

```bash
git clone https://github.com/FayaaDev/Rakkib.git
cd Rakkib
sudo -E bash install.sh
```

**Manual root-agent fallback** (only if you do not want the bootstrapper to launch the agent):

```bash
sudo -E $(command -v claude)    # or: sudo -E $(command -v opencode), sudo -E $(command -v codex)
```

> If `command -v` returns nothing, use the full path where you installed the binary (e.g., `sudo -E /home/ubuntu/.local/bin/opencode`). The `-E` flag preserves your `HOME` and agent credentials. This root launch is needed for the install run; Step 90 fixes ownership for later unprivileged maintenance.

Paste this prompt only when using the manual root-agent fallback or printed-prompt mode:

```text
Read README.md and AGENT_PROTOCOL.md first.

Use this repo as the installer.
Ask me the question files in order.
Record answers in .fss-state.yaml.
Do not write outside the repo until Phase 6 (questions/06-confirm.md).
On Linux, run only as root and use direct root commands after confirmation.
After confirmation, execute steps/00-prereqs.md through steps/90-verify.md in numeric order, skipping optional restore-test work unless explicitly requested.
Stop on any failed Verify block and fix it before continuing.
```

Expected flow:

1. The agent asks `questions/01-platform.md` through `questions/06-confirm.md`.
2. On fresh Ubuntu Linux installs, `install.sh` must run as root. If the plain `bash` path is used, it prints the explicit `curl ... | sudo -E bash` rerun command and exits. When running as root, the agent records `privilege_mode: root` and `privilege_strategy: root_process`.
3. After confirmation, the agent runs the deployment steps in numeric order, including Step 05 preflight.
4. The run is complete only when `steps/90-verify.md` passes, including the final ownership fix that ensures the repo is owned by the admin user for later unprivileged maintenance.
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
- Immich
- OpenClaw

OpenClaw install model in v1:
- When selected, install OpenClaw from npm as a user-scoped binary at `~/.local/bin/openclaw`.
- Require `node >= 22.14.0` and `npm` before rendering the host service wrapper.

Immich install model in v1:
- When selected, install CPU-only Immich using its dedicated Docker Compose stack.
- Use Immich's dedicated Postgres/Valkey services rather than the shared Rakkib PostgreSQL instance.

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

- `privilege_mode: root` on Linux, `sudo` on Mac
- `privilege_strategy: root_process` on Linux, `none` on Mac
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
- optional `https://{{IMMICH_SUBDOMAIN}}.<domain>`
- optional `https://{{OPENCLAW_SUBDOMAIN}}.<domain>`

with Caddy, Cloudflare Tunnel, and PostgreSQL configured in the same operating style as the source server.

## Linux Privileges

- Fresh Ubuntu Linux installs need a privileged account for Docker Engine installation and some service setup.
- **Canonical Linux install path:** Run `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | sudo -E bash`. The `-E` flag preserves agent credentials and the user environment.
- **Friendly first attempt:** `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash` may be used. On Linux it prints the explicit root rerun command and exits if it is not already root.
- **Local clone path:** If the repo is already cloned, run `sudo -E bash install.sh` from the repo root.
- If the agent is running unprivileged on Linux, it prints the same `curl ... | sudo -E bash` instruction and stops cleanly. Do not fall back to `sudo -S` or password-in-chat.
- Step 90 must fix repo and state-file ownership back to the admin user for later unprivileged maintenance.
- The host `cloudflared` CLI should be installed into the admin user's `~/.local/bin/cloudflared` when it is missing.

<!-- BEGIN BEADS INTEGRATION -->
## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Dolt-powered version control with native sync
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update <id> --claim --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task atomically**: `bd update <id> --claim`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Auto-Sync

bd automatically syncs via Dolt:

- Each write auto-commits to Dolt history
- Use `bd dolt push`/`bd dolt pull` for remote sync
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

<!-- END BEADS INTEGRATION -->
