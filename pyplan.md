# Rakkib v2 — Python binary replaces the markdown-driven agent loop

## Context

Rakkib v1 drives an LLM agent through `AGENT_PROTOCOL.md` + `questions/*.md`. The agent reads markdown, asks the user, writes `.fss-state.yaml`, then renders templates and runs `docker compose` while streaming output back through its context window. A dry-run on a fresh Linux box exposed three structural costs of that design:

1. The interview (phases 1–6) is mostly form-filling — validation, normalization, and conditionals are already encoded in the AgentSchema YAML blocks. Paying an LLM per turn to do this is expensive.
2. `docker compose up` streams layer-by-layer pull progress through the agent context, burning tokens on noise the agent doesn't act on.
3. Closing and reopening an AI session restarts the interview from question 1, because the prompt has no resume directive and the agent has no persistent state beyond `.fss-state.yaml` (which it isn't told to read first).

A Python binary fixes all three by construction: deterministic interview, native subprocess output, trivial resume. The agent is reduced to an *escape hatch* for the parts that genuinely need judgment.

---

## Architecture — wizard spine, agent escape hatch

The binary owns everything deterministic. The agent is invoked only when the binary explicitly hands off.

### Binary owns
- Phases 1–6 interview, driven directly by the AgentSchema YAML in each `questions/*.md`
- `.fss-state.yaml` read/write/merge and resume detection
- Host detection (`uname -m`, `id -u`, `hostname -I`, `ipconfig getifaddr en0`)
- Secret generation (openssl-backed)
- Template rendering (placeholder substitution per `lib/placeholders.md`)
- Steps 00 / 10 / 30 / 50 / 60 / 80 / 90 (prereqs, layout, caddy, postgres, services, cron, verify)
- Idempotent re-apply on every step

### Agent owns
- Step 40 Cloudflare auth handoff (browser flow, headless device flow, account ambiguity)
- Any failed `## Verify` block — binary launches the agent with a *narrow* prompt: failed step name, last N lines of the relevant log, the state slice it needs. Agent's job is "diagnose this one failure," not "drive the install."
- Post-install conversational mode (`rakkib add <service>`, `rakkib doctor --interactive`)

---

## Why Python (and the Go tradeoff)

Python is the right pick:
- Rakkib already shells out to `docker`, `openssl`, `cloudflared`, `psql` — no perf concern.
- Tiny dep set: `pyyaml`, `click` (or `typer`), `jinja2` (or plain `str.replace` per protocol rule 1), `rich` for nice prompts.
- Distribute as `pipx install rakkib` or `uv tool install rakkib` — both put a shim on PATH automatically.
- Lower contributor barrier than Go.

**Tradeoff to acknowledge:** Go would give a single static binary with no runtime dependency. On a truly fresh Linux box, Python 3 is preinstalled on every modern distro Rakkib targets (Ubuntu 22.04+, Debian 12+), so this is a small concern in practice. If it becomes one later, PyInstaller or a Go rewrite is a v2.1 decision.

---

## Project structure

```
rakkib/
  pyproject.toml
  src/rakkib/
    cli.py             # click entrypoint: init, doctor, status, add, uninstall
    state.py           # .fss-state.yaml load/save/merge
    schema.py          # parse AgentSchema YAML from questions/*.md
    interview.py       # phase loop: prompt -> validate -> normalize -> persist
    detect.py          # host detection helpers
    secrets.py         # generate POSTGRES_PASSWORD, AUTHENTIK_SECRET_KEY, etc.
    render.py          # placeholder substitution from state -> template files
    docker.py          # compose up/pull, health polling, log capture
    steps/
      prereqs.py       # step 00
      layout.py        # step 10
      caddy.py         # step 30
      cloudflare.py    # step 40 — orchestrates, hands off to agent for auth
      postgres.py      # step 50
      services.py      # step 60
      cron.py          # step 80
      verify.py        # step 90
    agent_handoff.py   # launch opencode/claude/codex with a narrow prompt
  tests/
  templates/           # unchanged
  registry.yaml        # extended with `image:` field per service
  questions/           # AgentSchema YAML becomes machine-authoritative
  AGENT_PROTOCOL.md    # demoted to human spec; no longer the runtime prompt
  install.sh           # installs Python if missing, then `pipx install .`
```

---

## Migration waves

Each wave is one PR. Each wave keeps `.fss-state.yaml` shape identical so a partially-migrated install still works.

**Wave 0 — bootstrap.** Update `install.sh` to ensure `python3` and `pipx` are present, then `pipx install` from the cloned repo. Keep the multi-shell PATH writing (Issue 1 from the prior plan) since pipx still relies on `~/.local/bin` being on PATH.

**Wave 1 — interview.** Implement `state.py`, `schema.py`, `interview.py`. Read AgentSchema YAML out of each `questions/*.md`, drive Phases 1–6 entirely in Python. Delete the agent-prompt path for the interview. Resume is automatic: load state, find first phase with unset required keys, start there. If `confirmed: true`, ask once whether to start over (overwriting `.fss-state.yaml`).

**Wave 2 — render + plumbing.** Implement `render.py`, `secrets.py`, `docker.py`. Port Steps 10, 30, 50, 60, 80, 90. Each step has `run()` and `verify()`; `verify()` returns ok or a structured failure (step, log path, state slice). Docker output redirects to `${DATA_ROOT}/logs/<step>.log` — issue 2 dissolves because no LLM is watching.

**Wave 3 — Cloudflare (Step 40).** Binary handles tunnel discovery, DNS routing, and the post-login wiring. For login itself, binary prints the URL and either waits on the local `cloudflared` callback (browser flow) or hands off to the agent with a narrow prompt for headless / api-token paths.

**Wave 4 — agent escape hatch.** Implement `agent_handoff.py`. On any `verify()` failure, binary asks "launch agent to diagnose? (Y/n)" and invokes the available agent with: failed step, log tail, relevant state keys, and the specific question files for that step — *not* `AGENT_PROTOCOL.md` whole.

**Wave 5 — post-install.** `rakkib add <service>` reuses the wizard for just that service's questions, runs only Step 60 for that service, updates state and the agent-memory README block. `rakkib status` prints what's deployed and which phase the binary would resume at.

---

## What this fixes vs the original three issues

| Issue | v1 fix (markdown plan) | v2 outcome |
|---|---|---|
| 1. Source bashrc | Write PATH to bashrc/zshrc/profile | Same fix carried forward; pipx adds its own PATH guarantee |
| 2. Docker pull tokens | New `rakkib pull` command | Gone by construction — no LLM in the loop |
| 3. Resume | Add Resume Rules to protocol + prompt | Trivial — binary reads state on startup |

The Wave 0 PATH fix is still needed. The `rakkib pull` command becomes optional polish (wall-clock parallelism only) and can ship later or never. The protocol resume rules are no longer needed — the binary just does it.

---

## Backwards compatibility

- `.fss-state.yaml` shape is unchanged. A user mid-install with a v1 state file can finish under v2 without editing anything.
- `registry.yaml` gains an `image:` field per service — additive, not breaking.
- `AGENT_PROTOCOL.md` and `questions/*.md` stay in the repo as human-readable spec; the AgentSchema YAML inside them becomes the single machine-authoritative source. Agents that someone wants to point at the repo manually can still read them.
- `bin/rakkib` (bash) is removed once `pipx install rakkib` is the install path. `cmd_uninstall` logic moves into the Python CLI.

---

## Key files

**Add:** `pyproject.toml`, `src/rakkib/**`, `tests/**`.
**Modify:** `install.sh` (Python + pipx bootstrap), `registry.yaml` (add `image:` per service).
**Demote:** `AGENT_PROTOCOL.md`, `questions/*.md` (still in repo, no longer runtime).
**Remove:** `bin/rakkib`, `lib/common.sh` (logic absorbed into Python), `scripts/rakkib-doctor` (becomes `rakkib doctor`).

---

## Verification (end-to-end)

1. **Fresh Ubuntu 24.04 VM.** `curl … install.sh | bash` → installs Python+pipx if missing → `rakkib init` runs the wizard. No LLM is invoked during phases 1–6.
2. **Token cost.** Same install with Authentik + Immich selected: zero LLM tokens consumed for the interview, zero for `docker compose up` progress.
3. **Resume.** Kill terminal halfway through Phase 3, relaunch `rakkib init` → resumes at Phase 3 question 2 silently. With `confirmed: true`, prompts "start over? (y/N)" once.
4. **Step failure path.** Force a Step 60 failure with a bogus image tag → binary prints the failure summary, offers "launch agent to diagnose? (Y/n)" → agent receives only the failure context, not the full protocol.
5. **Post-install add.** `rakkib add jellyfin` → prompts only Jellyfin's needed values → renders + runs only the Jellyfin slice of Step 60 → updates the agent-memory README block.
6. **Idempotent re-apply.** `rakkib init` on an already-deployed host is a no-op for everything that matches and a precise diff-and-merge for anything drifted, per `lib/idempotency.md`.

---

## Risks and open questions

- **Python availability on truly minimal images** (Alpine, distroless container hosts). Bootstrap should detect and either install or fail clearly.
- **Distribution channel.** DECISION (Rakkib-94m): v2.0 ships via a GitHub release wheel (`pipx install <release-asset-url>`). PyPI publication is deferred to v2.1+ for cleaner long-term discoverability. The release CI will build `py3-none-any.whl` and attach it to the GitHub release.
- **Test coverage.** v1 has no test suite I could find. v2 needs at least: schema parsing, state round-trip, render output snapshot, and a docker-mocked step happy-path test.
- **Marketing positioning.** "Agent-driven installer" becomes "wizard + agent for hard parts." Worth deciding before any public messaging change.
- **Existing `expansions.md` v1.1 services.** They land easier under v2 because adding a service is `registry.yaml` + template + maybe a step subclass, no markdown round-trip.

---

## Out of scope for v2.0

- Web/GUI wizard.
- Multi-host orchestration.
- Auto-detecting drift on a schedule.
- Replacing `cloudflared` with a Python tunnel client.
