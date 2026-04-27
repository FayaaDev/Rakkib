# CLAUDE.md

The `rakkib` Python binary owns the installer. It drives Phases 1–6, renders templates, runs steps, and manages `.fss-state.yaml`. **You are an escape hatch, not the driver.**

## When you are invoked

The binary hands off to Claude (or another agent) only in these situations:

1. **Step 40 — Cloudflare auth handoff.** Browser login on a headless server, API-token ambiguity, or account-selection judgment.
2. **A failed `## Verify` block.** The binary gives you a *narrow* prompt: failed step name, last N lines of the relevant log, the state slice you need, and the specific step file — **not** the full `AGENT_PROTOCOL.md`.
3. **Post-install conversational mode.** `rakkib doctor --interactive` or `rakkib add <service>` when the user asks follow-up questions that need judgment.

Do not attempt to run Phases 1–6 or Steps 00/10/30/50/60/80/90 yourself. The binary does that deterministically.

## Before you act

1. Read the specific step file the binary named in its handoff prompt.
2. Read `.fss-state.yaml` for the current state slice.
3. Read `lib/placeholders.md` and `lib/idempotency.md` for render and re-apply rules.
4. Do not write outside this repo until `questions/06-confirm.md` records `confirmed: true` in `.fss-state.yaml`.

## After the handoff

Return a concise diagnosis and the exact command or file change needed. The binary will apply it (or ask the user for confirmation). Do not stream `docker compose` output through your context window.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
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
