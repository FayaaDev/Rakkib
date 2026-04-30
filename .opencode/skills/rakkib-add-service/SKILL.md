---
name: rakkib-add-service
description: Add a new service to Rakkib using the registry-driven workflow, including registry entry, templates, hooks, and verification updates.
metadata:
  project: Rakkib
  scope: project-local
---

# Rakkib Add Service

## Goal

Add a new service to Rakkib so it works cleanly with:
- `rakkib init`
- `rakkib pull`
- `rakkib add <service>`
- registry consistency checks
- rendered output expectations where applicable

The service is not complete until it is available in both runtime flows:
- the registry-driven deploy/remove pipeline
- the Phase 3 interview service catalog in `src/rakkib/data/questions/03-services.md`

Prefer the registry-driven architecture. Do not add new hardcoded `if svc_id == ...` branches unless the behavior genuinely cannot be expressed through registry fields, templates, or hooks.

## Read First

Before editing, inspect these files:
- `/srv/apps/source/Rakkib/src/rakkib/data/registry.yaml`
- `/srv/apps/source/Rakkib/src/rakkib/data/questions/03-services.md`
- `/srv/apps/source/Rakkib/src/rakkib/steps/services.py`
- `/srv/apps/source/Rakkib/src/rakkib/steps/postgres.py`
- `/srv/apps/source/Rakkib/src/rakkib/hooks/services.py`
- `/srv/apps/source/Rakkib/src/rakkib/render.py`
- `/srv/apps/source/Rakkib/src/rakkib/cli.py`
- `/srv/apps/source/Rakkib/tests/test_registry_consistency.py`
- `/srv/apps/source/Rakkib/tests/test_phase3b_output_snapshot.py`
- `/srv/apps/source/Rakkib/tests/fixtures/sample_state.yaml`
- `/srv/apps/source/Rakkib/AGENTS.md`

## Ask For

If the user has not already specified them, gather these details:
- service id
- display label / product name
- foundation or optional placement
- docker image
- default port
- `host_service` and `host_port`
- default subdomain
- dependencies
- env keys
- generated secrets
- whether it uses shared Postgres
- whether it needs a monitoring block (and if so, what URL path to health-check, and whether the target is `public_url`, `host_port`, `container`, or `custom`)
- whether it needs Homepage metadata
- whether it needs persistent data dirs and chown
- whether it needs extra templates
- whether it needs custom hooks
- whether it should be public or auth-switchable in Caddy

## Implementation Rules

Use the smallest correct change.

Prefer these mechanisms in order:
1. Registry fields in `src/rakkib/data/registry.yaml`
2. Templates under `src/rakkib/data/templates/`
3. Existing shared hook infrastructure in `src/rakkib/hooks/services.py`
4. New hook functions only if the behavior is truly service-specific and cannot be represented declaratively

Keep Rakkib's constraints in mind:
- target machine is bare metal
- `install.sh` is sacred
- avoid assumptions about preinstalled host tooling
- do not design around testing on the current machine as the real validation happens on a fresh server

## Typical Files To Add Or Update

For a normal service, check whether you need:
- `src/rakkib/data/registry.yaml`
- `src/rakkib/data/questions/03-services.md`
- `src/rakkib/data/templates/docker/<id>/docker-compose.yml.tmpl`
- `src/rakkib/data/templates/docker/<id>/.env.example`
- `src/rakkib/data/templates/caddy/routes/<id>.caddy.tmpl`
- `src/rakkib/data/templates/caddy/routes/<id>-public.caddy.tmpl`

Only add the following when required:
- `extra_templates`
- `hooks`
- `postgres` block
- `homepage` block
- `data_dirs`
- `chown`
- `env_preserve_keys`
- `conditional_secrets`

## Template Safety Checks

Before finalizing any new service, validate the rendered templates as a system, not as isolated files.

### 1. Upstream Defaults vs Rakkib Service Names

If the upstream app expects peer services by hostname or container alias, verify that Rakkib uses the same names.

Common examples:
- app defaults to `database`, but Rakkib service is named `myapp-database`
- app defaults to `redis`, but Rakkib service is named `myapp-redis`
- app defaults to `localhost`, but the app actually runs in Docker and must use another service name

If Rakkib renames a dependency service, explicitly set the corresponding env vars in `.env.example`.

Do not assume upstream defaults remain correct after changing compose service names.

### 2. Compose References Must Match `.env.example`

For every `${VAR}` used in `docker-compose.yml.tmpl`, verify one of these is true:
- it is rendered into `.env.example`
- it is intentionally provided by Docker Compose or the shell at runtime
- it has a safe inline default in compose

Do not leave compose depending on values that are only created transiently in Python state unless those values are also written into `.env`.

### 3. Runtime Values Belong In `.env`

If a service needs dynamic values discovered during setup, such as:
- generated IDs
- allocated ports
- UID/GID mappings
- runtime hostnames

prefer this pattern:
- render the values into `docker/<id>/.env`
- reference them from compose using `${VAR}`

This prevents later re-renders from producing broken compose files.

### 4. Preserve Dynamic Env Keys

If step-specific logic writes dynamic values into `.env`, add those keys to `env_preserve_keys` in the registry entry unless overwrite-on-rerender is explicitly desired.

This is especially important for:
- tunnel UUIDs
- generated ports
- runtime user IDs
- user-supplied tokens or credentials that should survive later deploy flows

### 5. Check The Upstream Example Files

Read the upstream project's official `docker-compose.yml`, `.env`, or install docs before finalizing the Rakkib template.

Specifically compare:
- service names
- expected env variable names
- default hostnames
- required ports
- dependency assumptions

If Rakkib diverges from the upstream names, compensate explicitly in `.env.example` or compose.

### 6. Verify Fresh Render Output

Before finishing, inspect the rendered expectation logically and confirm:
- every inter-container hostname resolves to an actual compose service name
- every `${VAR}` in compose has a source
- no required env var is missing from `.env.example`
- no app dependency still points at an upstream default that Rakkib renamed
- the service can survive a later `rakkib pull` or `rakkib add` re-render without silently breaking

## Registry Checklist

When adding the registry entry, consider:
- `id`
- `state_bucket`
- `required` / `optional`
- `foundation: true` (explicit boolean required on foundation bundle services — distinct from `state_bucket: foundation_services`)
- `image`
- `container_name` if non-default
- `default_port`
- `host_service`
- `host_port`
- `default_subdomain`
- `subdomain_key`
- `subdomain_placeholder`
- `depends_on`
- `caddy` (dict with sub-key `template` for the route file name, and optionally `public_template` for a separate public-access variant)
- `env_keys`
- `secrets`
- `conditional_secrets`
- `postgres`
- `monitoring` (fields: `enabled`, `type`, `target`, `path`, `port`, `interval`, `timeout`, `retries`, `hostname`, `custom_url`, `name` — drives uptime-kuma sync hooks)
- `homepage`
- `data_dirs`
- `chown`
- `extra_templates`
- `hooks`
- `env_preserve_keys`
- `notes`

## Interview Catalog Checklist

When adding a user-selectable service, also update `src/rakkib/data/questions/03-services.md`:
- add the service to the correct `service_catalog` section
- add or shift the numeric alias so aliases stay unique
- update `fields.optional_services` or `fields.foundation_services`
- update the rendered checklist text under "Present This Menu"
- update the recorded `subdomains:` example and placeholder mapping list
- if the service is host-backed, describe it accurately in the menu text instead of implying it is containerized

## Verification Checklist

Before finishing:
1. Confirm every referenced template path exists.
2. Confirm every referenced hook name resolves in the hook registries. Note: `test_registry_consistency.py` automatically checks `post_render`, `pre_start`, and `post_start` hook names — `restart` and `remove` hooks are NOT covered by that test and must be verified manually.
3. Confirm the service is discoverable from `registry.yaml` by id.
4. Confirm the service appears in `rakkib init` via `src/rakkib/data/questions/03-services.md`.
5. Confirm `rakkib add <id>` has what it needs:
   - valid bucket
   - valid dependencies
   - valid subdomain behavior
6. Confirm service-to-service hostnames are valid after any Rakkib-specific renaming.
7. Confirm every compose `${VAR}` is sourced from `.env.example`, shell runtime, or an intentional inline default.
8. If dynamic values are generated during setup, confirm they are persisted in `.env` when later re-renders depend on them.
9. Update tests that assert Phase 3 service catalog contents when you add or reorder services.
10. Update `tests/test_registry_consistency.py` only if the existing generic assertions are no longer sufficient.
11. If rendered outputs change materially, update fixture or snapshot expectations.

## Completion Standard

A service addition is only complete when the repo contains the full declarative definition and all referenced assets needed for the service to deploy through the existing pipeline without ad hoc follow-up edits.
