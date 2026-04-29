# Rakkib v2 — Cleanup, Tighten, and Streamline Service Additions

## Context

Rakkib was an agent-driven app in v1 — an LLM read step markdown files (`data/steps/*.md`, `data/lib/*.md`, `data/tasks/*.md`) and walked the user through interactive setup. v2 replaced that with a self-contained `rakkib` Python CLI (Click + Questionary + Rich) under `src/rakkib/`. The migration left v1 docs, build artifacts, dead code paths, hardcoded service-id branches, and double-executions in place.

This plan lands three things, in order of risk:

1. **Cleanup** — delete v1 leftovers and untracked build artifacts. Pure subtraction; no behavior change.
2. **Tighten** — collapse duplications, fix one dead `if`, fix one redundant write, kill the verify-triple-run, single source of truth for step ordering.
3. **Streamline service additions** — push hardcoded service-id branches in `services.py`/`postgres.py` into `registry.yaml` so adding a new service is "edit YAML + drop in templates" with zero Python edits.

Phases 1–2 alone cut ~400 lines of code and ~9 markdown files from the wheel, fix one observable performance bug (verify runs each step's checks 3×), and remove one unreachable-code wart. Phase 3 is the bigger structural win the user asked for; per the user's decision, it ships across two follow-up PRs (3a data-only, 3b hooks/factories) after Phases 1+2 land.

---

## Phase 1 — Stale-code cleanup

All deletes. No semantic change.

### 1.1 Untracked artifacts on disk (already in `.gitignore`, but cluttering the working tree)

| Path | Action |
|---|---|
| `MagicMock/` (contains a single file literally named `run_interview().get()`) | `rm -rf` |
| `build/` (setuptools output; mirror of `src/rakkib/` plus the v1-only `build/lib/rakkib/agent_handoff.py`) | `rm -rf` |
| `src/rakkib.egg-info/` | `rm -rf` |
| `.DS_Store` (currently **tracked** in git) | `git rm`, then add `.DS_Store` to `.gitignore` |

### 1.2 Stale `data/` subdirectories shipped in the wheel (zero Python references)

`pyproject.toml` packages `data/**/*`, so every byte below ships in the wheel for nothing.

| Path | Why stale | Confirmed by |
|---|---|---|
| `src/rakkib/data/lib/` (`idempotency.md`, `placeholders.md`, `question-schema.md`) | v1 LLM-readable spec; only mention is a docstring in `render.py:3` | grep |
| `src/rakkib/data/tasks/` (`lessons.md`, `todo.md`) | v1 agent task notes | grep |
| `src/rakkib/data/steps/*.md` (9 files) | v1 step playbooks; logic now in `src/rakkib/steps/*.py` | grep |
| `src/rakkib/data/templates/launchd/` (only `.gitkeep`) | empty placeholder | listing |
| `src/rakkib/data/templates/systemd/` (empty) | unreferenced | listing |

### 1.3 Stale Python modules (zero source-tree imports)

| Path | Why stale | Action |
|---|---|---|
| `src/rakkib/detect.py` | No source module imports `rakkib.detect`. The `_run_detect` in `interview.py:241` is unrelated (it execs YAML-supplied shell commands, not these helpers). | delete file |
| `src/rakkib/validate.py` | No source module imports it. `interview.py` defines its own inline `_validate` (line 593) with a re.match-vs-re.search anchoring divergence. Only `tests/test_validate.py` references it. | delete file |
| `tests/test_validate.py` | Tests the dead module. | delete |
| `tests/test_e2e_verification.py` | Imports `rakkib.agent_handoff` (lines 194, 195, 243, 244, 435) — module no longer exists in `src/rakkib/`. Tests must be erroring on collection. | delete |

### 1.4 Dead functions inside live modules

| Item | Why dead | Action |
|---|---|---|
| `interview.py:181-189` `_customize_subdomains` | Defined but never called; `_handle_repeat` inlines its own customization loop | delete function |
| `cli.py:42-46` `_require_root` | Defined but never called; `privileged` group at `cli.py:594-596` reimplements the same check inline | delete function (or, optionally, refactor `privileged` to call it) |
| `state.py` `merge` and `_deep_merge` | `State.merge` is never called from `src/`. | delete unless tests rely on it |
| `interview.py:236-237` `derived_value` branch in `_handle_derived` | No question YAML uses `derived_value:` (verify with `grep -n "^    derived_value:" data/questions/*.md`). `_record_field_value` (line 637) also references it; remove together. | delete branch + the reference at line 637 |

### 1.5 Stale `docs/` files

| Path | Why stale |
|---|---|
| `docs/vergo-history/` (Plan1.md, Plan2.md, `@`) | "vergo" was the v1 codename |
| `docs/WORKFLOW_RULES.md` | v1 agent orchestration rules ("Plan Node Default", "STOP and re-plan") |
| `docs/3bugfixes.md` | Self-describes as v1 dry-run feedback resolved by v2 |
| `docs/expansions.md` | "Rakkib v1.1 — Tool Expansion Plan" |
| `docs/question-schema.md` | References `AGENT_PROTOCOL.md` (no longer exists); schema now self-documenting in `src/rakkib/schema.py` |

`docs/REFERENCE_SERVER.md`, `docs/runbooks/`, `docs/beads*.md` stay — still relevant.

### 1.6 Cosmetic doc fixes

- `tui.py:3` — drop the "decouples interview.py and agent_handoff.py" mention from the docstring (no longer accurate).
- `render.py:3` — drop the `lib/placeholders.md` reference (file is being deleted).
- `AGENTS.md` and `CLAUDE.md` are **both** kept — they're consumed by different tools (Claude Code auto-loads `CLAUDE.md`; `AGENTS.md` is read by Codex and other agentic tools). Diff them and dedup any drifted content so they stay in sync, but do **not** merge into a single file.

---

## Phase 2 — Tighten

Small refactors that fix double-execution, dedup, and put the step-ordering on a single source of truth.

### 2.1 `STEP_MODULES` single source of truth

**Problem:** `cli.py:128-136` (`_run_steps`) and `verify.py:24-31` (`_collect_verifications`) both hardcode the step list. Drift silently breaks Step 7.

**Fix:** add to `src/rakkib/steps/__init__.py`:

```python
STEP_MODULES: list[tuple[str, str]] = [
    ("layout",     "rakkib.steps.layout"),
    ("caddy",      "rakkib.steps.caddy"),
    ("cloudflare", "rakkib.steps.cloudflare"),
    ("postgres",   "rakkib.steps.postgres"),
    ("services",   "rakkib.steps.services"),
    ("cron",       "rakkib.steps.cron"),
]
```

`_run_steps` enumerates this + appends a virtual `("verify", "rakkib.steps.verify")` entry. `_collect_verifications` consumes the list directly.

### 2.2 Kill the verify triple-run

**Problem:** Each step's `verify()` runs three times per `pull`:
1. After its own `run()` in `cli._run_steps:152`.
2. Inside `verify.run` → `_collect_verifications`.
3. Inside `verify.verify` (called from `cli._run_steps:152` for Step 7 itself) → `_collect_verifications` again.

Cloudflared verify polls 20 × 3s = up to 60s; postgres `pg_isready`; caddy curl. Triple-running is a real wall-clock cost on a fresh bring-up.

**Fix:**
- In `cli._run_steps`, store each step's `VerificationResult` on `state` (or a local list passed forward). For the final `verify` step, skip the post-run `verify_fn` call.
- `verify.py` reads the cached results and aggregates. If a step's result is missing (e.g., `pull` was resumed mid-flight), it falls back to calling that step's `verify()`.

### 2.3 Cache `_load_registry`

**Problem:** `services.py:42-44` re-opens and re-parses `registry.yaml` on every call. Called 5+ times per `pull` and `add`.

**Fix:** `@functools.lru_cache(maxsize=1)` on `_load_registry`. Trivial.

### 2.4 Extract doctor table helper

**Problem:** `cli.py:253-268` and `cli.py:302-315` build identical Rich tables differing only in `title=`.

**Fix:** extract `_render_doctor_table(checks: list[Check], title: str) -> Table` and call it twice.

### 2.5 Fix unreachable `write_text` in postgres step

**Problem:** `steps/postgres.py:148-150`:

```python
env_path.write_text(merged)
if not env_path.exists():     # always False — line above just created it
    env_path.write_text(merged)
```

**Fix:** delete lines 149-150.

### 2.6 Avoid re-generating SQL

**Problem:** `steps/postgres.py:156` and `:181` both call `_generate_init_sql(state)`.

**Fix:** generate once into a local `sql = _generate_init_sql(state)`; reuse.

### 2.7 Don't recursively chown service-managed UIDs

**Problem:** `cli.py:610-637` `privileged_ensure_layout` chowns each path **and** `os.walk`s it. The first `paths` entry is `Path(data_root)` (default `/srv`). On a populated server this walks the entire data tree (n8n's UID 1000 dirs, postgres data dirs with rootless UIDs, etc.) and chowns them to the admin user — both slow and potentially destructive to bind-mount permissions.

**Fix:** keep recursive chown for the layout dirs Rakkib itself creates (`docker/`, `apps/static/`, `MDs/`, `backups/` — admin-owned by design) and chown only the top-level node for `data/`. Per-service handlers already set the correct UID:GID inside `data/<svc>/` and we must not stomp on them.

### 2.8 `subdomain_placeholder_key` helper

**Problem:** `f"{slug.upper().replace('-', '_')}_SUBDOMAIN"` appears 4× (`interview.py:178, 189, 490, 494`).

**Fix:** add `subdomain_placeholder_key(slug)` helper in `state.py` (or a new `keys.py`); use everywhere. Long-term, registry already declares `subdomain_placeholder` per service — read it instead of computing.

### 2.9 Cron marker substring → endswith

**Problem:** `steps/cron.py:53` filters out lines containing the rakkib marker substring. A user comment containing the marker would be silently dropped on idempotent re-install.

**Fix:** anchor with `line.endswith(marker)` (consistent with how `_install_cron_entry` writes the line).

### 2.10 Hoist single-use Jinja `Environment`

**Problem:** `render.py:50` constructs a fresh `Template(...)` per call → parse + compile every time. `render_tree` runs this for dozens of `.tmpl` files per pull.

**Fix:** module-level `Environment(undefined=DebugUndefined)` and `env.from_string(template_text)`. Use the existing env's caching.

### 2.11 Hoist regex constants

- `interview.py:299` `re.findall(r"\{\{([^{}]+)\}\}", ...)` — already exists in `render.py` as `PLACEHOLDER_RE` with stricter charclass; align and import once.
- `cli.py:428` `^[a-z0-9-]+$` for subdomain validation — lift to `_RX_SUBDOMAIN` at module top so `init` (via question YAML) and `add` agree.
- `normalize.py:38, 48, 54, 68` — hoist `_RX_IN`, `_RX_IS_NOT_NULL`, `_RX_EQ`, `_RX_NEQ` to module top.

### 2.12 Cron unused locals

`steps/cron.py:171-179` — `selected = ...` and `platform = ...` computed inside `verify` but never read. Delete.

### 2.13 `eval_when` duplication

`state.py` (lines ~114-156) and `normalize.py` both implement `_eval_when`. They diverge on `or` support. State's resume-phase logic should call `normalize.eval_when` to avoid drift.

**Caveat before unifying:** audit every existing `when:` expression in `data/questions/*.md`. If the state.py path was relied on for *not* recognizing `or` (e.g., a phrase containing the literal substring "or" in a value), unifying activates it as a new operator and changes evaluation. Grep for `when:` and confirm no live expression regresses; only then merge.

---

## Phase 3 — Streamline service additions (registry-driven)

This is the big architectural win. After this phase, **adding a new service is: drop three template files + add one YAML block. No Python edits.**

### Hardcoded service-id branches today

Every item below is a Python branch keyed on `svc_id`:

| # | Where | What's hardcoded | Lines |
|---|---|---|---|
| A | `services.py` `_render_caddy_route` | `auth_switchable = ("homepage", "uptime-kuma", "dockge", "n8n")` selecting `<id>.caddy.tmpl` vs `<id>-public.caddy.tmpl` | 182-184 |
| B | `services.py` `_deploy_single_service` | `if/elif svc_id == ...` dispatch into `_handle_authentik`/`_handle_homepage`/`_handle_n8n`/`_handle_immich`/`_handle_transfer` | 439-450 |
| C | `services.py` `_handle_homepage` | `_HOMEPAGE_CARDS` dict (category, name, description, icon) for each service | 274-284 |
| D | `services.py` `_generate_missing_secrets` | Per-service `_ensure(...)` blocks for secret keys + factories; cross-service `nocodb && authentik → OIDC pair`; `n8n_mode == "fresh"` gate | 85-129 |
| E | `services.py` `verify` | `if svc_id == "authentik": container_name = "authentik-server"` etc. | 572-576 |
| F | `services.py` `_deploy_single_service` | Per-service `preserve = [...]` env keys (n8n: `N8N_ENCRYPTION_KEY`; immich: `IMMICH_DB_PASSWORD`, `IMMICH_VERSION`) | 411-415 |
| G | `services.py` `_deploy_single_service` | NocoDB OIDC line uncomment in rendered `.env` when Authentik is in foundation | 418-431 |
| H | `services.py` | `_preflight_authentik_postgres` + `_wait_authentik_healthy`, dispatched via `if svc_id == "authentik"` | 453-461 |
| I | `services.py` `_handle_authentik` | `blueprint_map` dict listing per-service Authentik blueprint templates | 248-261 |
| J | `postgres.py` `_generate_init_sql` | Per-service hardcoded `if "nocodb" in foundation` etc. emitting SQL for role/db/password | 60-95 |
| K | `services.py` `_handle_authentik`/`_handle_n8n`/`_handle_transfer` | Hardcoded `data_dirs` + chown UID:GID per service | 230-345 |

### Target registry schema

A complete service entry after Phase 3 (using NocoDB as example):

```yaml
- id: nocodb
  state_bucket: foundation_services
  required: false
  optional: true
  foundation: true
  image: nocodb/nocodb:latest
  container_name: nocodb                      # (E) default: id
  default_port: 8080
  host_service: false
  host_port: false
  default_subdomain: nocodb
  subdomain_key: nocodb
  subdomain_placeholder: NOCODB_SUBDOMAIN
  depends_on: [postgres]

  # (A) Caddy route. public_template = used when authentik not active.
  caddy:
    template: nocodb.caddy.tmpl
    # public_template: nocodb-public.caddy.tmpl

  # (K) Filesystem prep
  data_dirs: [data/nocodb]
  # chown: { uid: 1000, gid: 1000 }            # optional; linux-only

  # (B) Bespoke renders / hooks (resolved against rakkib/hooks/services.py)
#   extra_templates:
  #   - { src: templates/docker/n8n/.env.tmpl, dst: docker/n8n/.env }
  # hooks:
  #   pre_start:   [authentik_postgres_preflight]
  #   post_render: [homepage_services_yaml, authentik_blueprints]
  #   post_start:  [authentik_wait_healthy]
  # health: { timeout: 360 }

  # (F) Preserve user-edited keys across re-renders
  env_preserve_keys: []                        # e.g. [N8N_ENCRYPTION_KEY]

  env_keys: [NOCODB_DB_PASS, ADMIN_EMAIL, NOCODB_ADMIN_PASS,
             NOCODB_OIDC_CLIENT_ID, NOCODB_OIDC_CLIENT_SECRET]

  # (D) Secret generation
  secrets:
    NOCODB_DB_PASS:    { factory: password }
    NOCODB_ADMIN_PASS: { factory: password }
  conditional_secrets:
    - when_services: [authentik]
      keys:
        NOCODB_OIDC_CLIENT_ID:     { factory: oidc_client_id }
        NOCODB_OIDC_CLIENT_SECRET: { factory: oidc_client_secret }

  # (J) Shared-postgres provisioning
  postgres:
    role: nocodb
    db: nocodb_db                              # default = role
    password_key: NOCODB_DB_PASS
    display_name: NocoDB

  # (I) Authentik proxy blueprint emitted only when authentik is selected
  authentik:
    blueprint: templates/docker/authentik/blueprints/nocodb.yaml.tmpl

  # (C) Homepage card
  homepage:
    category: Infrastructure
    name: NocoDB
    description: No-code database UI
    icon: nocodb.png

  notes: "..."
```

### Code changes per item

- **(A)** `_render_caddy_route` reads `svc["caddy"]["template"]` and `svc["caddy"].get("public_template")`. Hardcoded tuple disappears.
- **(B + H + K)** Add `src/rakkib/hooks/services.py` with `POST_RENDER_HOOKS: dict[str, Callable]`, `PRE_START_HOOKS`, `POST_START_HOOKS`. Three hooks survive: `homepage_services_yaml`, `authentik_blueprints` (consuming I), `authentik_wait_healthy`/`authentik_postgres_preflight`. Registry references hooks by string name. `_deploy_single_service` runs `data_dirs` mkdir, chown, then declared hooks via dict lookup. The `if/elif` chain dies.
- **(C)** `_HOMEPAGE_CARDS` deletes; `homepage_services_yaml` hook walks `all_selected` and reads `svc["homepage"]` from the loaded registry.
- **(D)** `_generate_missing_secrets` becomes a single double-loop: for each selected service, for each key in `svc.get("secrets", {})`, call the factory. Conditional secrets evaluated after the main loop with a service-membership check. Factories registered in `secrets.py` as `FACTORIES: dict[str, Callable] = {"password": generate_password, "secret_key": generate_secret_key, ...}`.
- **(E)** `container_name = svc.get("container_name", svc_id)`.
- **(F)** `preserve = svc.get("env_preserve_keys", [])`.
- **(G)** Move OIDC enable into the NocoDB `.env.example` template as `{% if authentik_enabled %}NC_OIDC_*=...{% endif %}`. **Caveat:** `render.flatten_state` joins lists with `\n`, so `'authentik' in foundation_services` does substring matching that would also match `authentikfoo`. Fix: emit a per-service `<id>_enabled` boolean into the template context (or override `flatten_state` to keep lists as lists).
- **(I)** Each consuming service declares `authentik.blueprint`; `authentik_blueprints` hook iterates selected services and renders any with that block. The hardcoded `blueprint_map` dict disappears.
- **(J)** `_generate_init_sql` walks the selected services, picks those with a `postgres:` block, emits SQL via the existing `_add_service` helper. **Order-of-operations:** lift the registry-loading + selected-service walk into `src/rakkib/steps/__init__.py` (e.g. `selected_service_defs(state) -> list[dict]`) **before** landing J. Otherwise `postgres.py` would have to import from `services.py`, which inverts the current dependency direction (`services.py` is downstream of `postgres.py` in the step pipeline).
- **(K)** Registry holds `data_dirs` + optional `chown`. The chown is linux-gated (matching today's behavior).

### `cli.py add` after Phase 3

The `add` command becomes pure registry mechanics:
- Bucket placement collapses to `state.append_to_bucket(svc["state_bucket"], service)`.
- Subdomain validation reuses the lifted `_RX_SUBDOMAIN` constant from Phase 2.11.
- All other steps (`depends_on`, `subdomain_placeholder` aliasing, `state_bucket == "always"` guard) are already registry-driven.

---

## Critical files modified

**Phase 1**: deletes only.

**Phase 2**:
- `src/rakkib/steps/__init__.py` — add `STEP_MODULES`
- `src/rakkib/cli.py` — consume `STEP_MODULES`, extract `_render_doctor_table`, scope `privileged_ensure_layout` chown, lift `_RX_SUBDOMAIN`
- `src/rakkib/steps/verify.py` — read cached results from `state`/passed list; fall back if missing
- `src/rakkib/steps/services.py` — `@lru_cache` `_load_registry`
- `src/rakkib/steps/postgres.py` — drop unreachable `write_text`; reuse SQL local
- `src/rakkib/steps/cron.py` — `endswith` marker check; delete unused locals
- `src/rakkib/render.py` — module-level Jinja `Environment`
- `src/rakkib/normalize.py` — hoist regex constants
- `src/rakkib/state.py` — reuse `normalize.eval_when`; add `subdomain_placeholder_key` helper

**Phase 3**:
- `src/rakkib/data/registry.yaml` — schema additions (caddy, data_dirs, chown, secrets, postgres, authentik, homepage, container_name, env_preserve_keys, hooks)
- `src/rakkib/steps/services.py` — collapses to a registry walker with hook dispatch (~150 fewer lines)
- `src/rakkib/steps/postgres.py` — `_generate_init_sql` becomes a registry walk
- `src/rakkib/data/templates/docker/nocodb/.env.example` — wrap OIDC lines in `{% if authentik_enabled %}`
- `src/rakkib/render.py` — emit per-service `<id>_enabled` boolean OR keep lists as lists in `flatten_state`
- `src/rakkib/secrets.py` — `FACTORIES` dict; `Callable` annotation fix
- New: `src/rakkib/hooks/services.py` — three hook callables registered by name

---

## Reusable utilities to lean on

- **`render.py`** already exports `render_string`, `render_text`, `render_file`, `render_tree` — the registry-driven `_deploy_single_service` reuses these for `extra_templates`.
- **`docker.py`** already exports `network_exists`, `create_network`, `compose_up`, `health_check`, `container_running`, `container_publishes_port`, `capture_container_logs` — `caddy.py:33-44` should replace the inline `docker network` calls with `network_exists` + `create_network`.
- **`secrets.py`** already exports `generate_password`, `generate_secret_key`, `generate_oidc_client_id`, `generate_oidc_client_secret` — Phase 3.D's `FACTORIES` dict just maps strings to these.

---

## Verification

The user explicitly said "Don't debug and run tests on current machine, the app is being tested on a bare metal machine. Not this one." Verification will be a combination of unit tests on this machine and a fresh-install dry-run on the bare-metal target.

### On this machine (this repo)

1. `python -m pytest tests/` after each phase — passes (test_validate.py + test_e2e_verification.py removed; test_interview.py customize-True tests removed alongside the dead branch).
2. `python -m compileall src/` — no syntax errors.
3. `pip install -e .` then `rakkib --help`, `rakkib status`, `rakkib doctor --json` — all commands resolve and emit expected output without exceptions on an unconfigured state.
4. After Phase 3 only: pre-flight check that for every service in the registry, the hooks/templates declared by string name actually exist on disk. A small `tests/test_registry_consistency.py` that loads `registry.yaml` and asserts every `caddy.template`, `extra_templates.src`, `authentik.blueprint`, and `hooks.*.<name>` is resolvable.
5. **Output-equivalence diff for Phase 3** (the highest-risk phase). On a frozen sample state YAML (`tests/fixtures/sample_state.yaml` covering one of every selected service), run the current `main` step pipeline against a tmp output directory, then run the Phase-3 branch against another tmp output directory, then `diff -r` the two trees. Allowed differences: secret values (random) and any timestamps. Everything else (Caddyfile, every `.env`, every `docker-compose.yml`, the postgres init SQL, the homepage `services.yaml`, the Authentik blueprints) must be byte-for-byte identical, modulo whitelisted volatile fields. This is the only verification that catches the registry refactor silently changing what gets deployed.

### On the bare-metal target (after merging)

1. `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash` on a fresh Ubuntu 24.04 server. Expect the existing pull flow to behave identically (same containers, same Caddy routes, same Postgres roles).
2. `rakkib pull` to a clean target — measure wall-clock against current main. Phase 2.2 (verify single-run) should drop ~1–3 minutes off the verification block.
3. `rakkib add jellyfin` against a server that didn't select jellyfin originally — confirms Phase 3 didn't regress the `add` path.
4. Spot-check a Phase-3 added service: drop a hypothetical `data/registry.yaml` entry + minimal templates for a placeholder service, run `rakkib add <id>`, confirm container starts and Caddy route resolves — without any Python edits.

---

## Progress tracker

As each item is completed, replace the `[ ]` with `[x] **done**` and (where useful) a one-line note. Update this file after every step — never batch.

### Phase 1 — Cleanup
- [x] **done** 1.1 Untracked artifacts — `rm -rf MagicMock/ build/ src/rakkib.egg-info/`; `git rm .DS_Store`; added `.DS_Store` to `.gitignore`
- [x] **done** 1.2 Stale `data/` subdirs — deleted lib/, tasks/, steps/ (9 md files), templates/launchd/ (.gitkeep), templates/systemd/ (empty). Kept templates/vergo/ (user confirmed WIP port).
- [x] **done** 1.3 Stale Python modules — `git rm detect.py validate.py tests/test_validate.py tests/test_e2e_verification.py`
- [x] **done** 1.4 Dead functions — deleted `_customize_subdomains`, `_require_root`, `derived_value` branch in `_handle_derived` + `_record_field_value`, customize=True branch in `_handle_repeat`, 2 dead tests. Kept `State.merge`/`_deep_merge` (still exercised in `test_state.py`).
- [x] **done** 1.5 Stale `docs/` files — deleted vergo-history/ (3 files), WORKFLOW_RULES.md, 3bugfixes.md, expansions.md, question-schema.md. Kept REFERENCE_SERVER.md, runbooks/, beads*.md.
- [x] **done** 1.6 Cosmetic doc fixes — `tui.py` docstring updated, `render.py` lib/placeholders.md ref removed, AGENTS.md synced with CLAUDE.md's two extra lines.

### Phase 2 — Tighten
- [x] **done** 2.1 `STEP_MODULES` single source of truth — added to `steps/__init__.py`, consumed by cli.py and verify.py
- [x] **done** 2.2 Kill the verify triple-run — cli._run_steps caches VerificationResults in state; verify.py reads cache, skips re-run
- [x] **done** 2.3 `@lru_cache` on `_load_registry`
- [x] **done** 2.4 Extract `_render_doctor_table` — cli.py now has helper, both doctor table builds use it
- [x] **done** 2.5 Drop unreachable `write_text` in postgres step
- [x] **done** 2.6 Reuse `_generate_init_sql` result — hoisted to `sql = _generate_init_sql(state)` local
- [x] **done** 2.7 Scope `privileged_ensure_layout` chown — recurse admin_dirs (docker/, apps/static/, backups/, MDs/); top-level only for data/ and root
- [x] **done** 2.8 `subdomain_placeholder_key` helper — added to state.py, 2 usages in interview.py updated
- [x] **done** 2.9 Cron marker `endswith` check
- [x] **done** 2.10 Hoist Jinja `Environment` to module level; render_tree now computes context once
- [x] **done** 2.11 Hoist regex constants — normalize.py 4 constants; interview.py `_TEMPLATE_KEY_RE`; cli.py `_RX_SUBDOMAIN`
- [x] **done** 2.12 Drop unused `selected`/`platform` locals in cron verify
- [x] **skipped** 2.13 Unify `eval_when` — `when: N8N_ENCRYPTION_KEY is null` (questions/05-secrets.md:64) would regress; normalize.eval_when lacks `is null` branch. Safe in a follow-up that adds `is null` first.

### Phase 3a — Data-only registry additions
- [x] **done** A `_render_caddy_route` reads `caddy.template`/`caddy.public_template` — auth/public route selection now comes from `registry.yaml`
- [x] **done** E `container_name` from registry — `services.verify()` now uses `svc.get("container_name", svc_id)`
- [x] **done** F `env_preserve_keys` from registry — removed the inline n8n/immich preserve-key branch
- [x] **done** K `data_dirs` + optional `chown` from registry — added `_prepare_service_data()` and removed hardcoded n8n/immich/transfer filesystem prep

### Phase 3b — Hooks layer + secrets/postgres walk
- [x] **done** Lift `selected_service_defs` topo-sort helper to `steps/__init__.py` — added shared `load_service_registry()`, `selected_service_defs()`, and `service_enabled_key()`
- [x] **done** B `if/elif svc_id` dispatch → `hooks/services.py` registry — service deploy now runs named `post_render`/`pre_start`/`post_start` hooks
- [x] **done** C `_HOMEPAGE_CARDS` → registry `homepage:` block — homepage YAML now renders from per-service registry metadata
- [x] **done** D `_generate_missing_secrets` → registry `secrets:`/`conditional_secrets:` walk + `FACTORIES` dict
- [x] **done** G NocoDB OIDC gating moves into `.env.example` template + per-service `<id>_enabled` boolean
- [x] **done** H Authentik pre/post-start hooks moved behind hook registry
- [x] **done** I `blueprint_map` → registry `authentik.blueprint`
- [x] **done** J `_generate_init_sql` walks selected services with `postgres:` block
- [x] **done** `tests/test_registry_consistency.py` (paths/hooks resolvable)
- [x] **done** Output-equivalence snapshot check on a frozen sample state YAML — added `tests/fixtures/sample_state.yaml`, expected rendered outputs under `tests/fixtures/phase3b_expected/`, and `tests/test_phase3b_output_snapshot.py`

---

## Confirmed decisions

1. **`pyqr.md`** — keep. WIP spec for a QR-code Cloudflare login feature; do not delete in Phase 1.
2. **vergo terminal addon** (`data/files/vergo/`, `data/templates/vergo/`, host_addons → vergo_terminal) — keep. Will be ported to v2 in a later PR; leave the assets and the host_addons offering in place.
3. **`customize_subdomains` prompt** — intentional UX simplification. Delete `_customize_subdomains` (`interview.py:181-189`), delete the customize=True branch in `_handle_repeat` (`interview.py:479-491`), and delete the two tests at `tests/test_interview.py:607-620` and `:739-741` that exercise the branch directly.
4. **Phase 3 sequencing** — wave it. Three PRs:
   - **PR #1** — Phases 1 + 2 (cleanup + tighten). Highest confidence, smallest blast radius.
   - **PR #2 (Phase 3a)** — pure data additions: items **A** (caddy templates), **E** (container_name), **F** (env_preserve_keys), **K** (data_dirs/chown). No behavior change; just reads from the registry instead of inline tuples/dicts.
   - **PR #3 (Phase 3b)** — hooks layer: items **B** (dispatch via `hooks/services.py`), **C** (homepage cards), **D** (secret factories), **G** (NocoDB OIDC template gating), **H** (authentik pre/post-start hooks), **I** (authentik blueprint registry), **J** (postgres init SQL walk; lift topo helper to `steps/__init__.py` first).
