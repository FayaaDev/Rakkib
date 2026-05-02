---
name: rakkib-add-service
description: Add a new service to Rakkib using the registry-driven workflow, including registry entry, templates, hooks, and verification updates.
metadata:
  project: Rakkib
  scope: project-local
---

# Rakkib Add Service

## Goal

Service is complete only when it works cleanly with `rakkib init`, `rakkib pull`, `rakkib pull --service <id>`, `rakkib add <service> --yes`, `rakkib smoke <service>`, and the Phase 3 interview catalog (`src/rakkib/data/questions/03-services.md`). Do not add hardcoded `if svc_id == ...` branches unless behavior cannot be expressed declaratively.

## Read First

- `src/rakkib/data/registry.yaml`
- `src/rakkib/data/questions/03-services.md`
- `src/rakkib/steps/services.py` & `steps/postgres.py`
- `src/rakkib/hooks/services.py`
- `src/rakkib/render.py` & `cli.py`
- `tests/test_registry_consistency.py` & `test_phase3b_output_snapshot.py`
- `tests/fixtures/sample_state.yaml`
- `AGENTS.md`

## Gather From User

- service id, display label, category (foundation / optional)
- docker image, default port, `host_service`, `host_port`, default subdomain
- dependencies, env keys, generated secrets
- shared Postgres? monitoring? Homepage metadata?
- persistent `data_dirs` + chown? extra templates? custom hooks?
- public or auth-switchable Caddy route?
- does any hook run host package-manager commands (`apt`, `curl | bash`, etc.)?

## Implementation Order

1. Registry fields in `src/rakkib/data/registry.yaml`
2. Templates under `src/rakkib/data/templates/`
3. Existing shared hooks in `src/rakkib/hooks/services.py`
4. New hook functions only when behavior is truly service-specific

Target is bare metal — avoid host tooling assumptions; do not test on the current machine.

### Host Installer Safety

Prefer Docker-only services. When a host installer is unavoidable:
- Route through shared hook runner (`_run_as_user` / `_run_as_service_user`), not bare `subprocess.run`
- Always wait for apt/dpkg locks
- Required noninteractive env: `DEBIAN_FRONTEND=noninteractive`, `APT_LISTCHANGES_FRONTEND=none`, `NEEDRESTART_MODE=a`, `NEEDRESTART_SUSPEND=1`, `UCF_FORCE_CONFFOLD=1`

## Typical Files

Always needed:
- `src/rakkib/data/registry.yaml`
- `src/rakkib/data/questions/03-services.md`
- `src/rakkib/data/templates/docker/<id>/docker-compose.yml.tmpl`
- `src/rakkib/data/templates/docker/<id>/.env.example`
- `src/rakkib/data/templates/caddy/routes/<id>.caddy.tmpl` (+ `<id>-public.caddy.tmpl` if needed)

Add only when required: `extra_templates`, `hooks`, `postgres`, `homepage`, `data_dirs`, `chown`, `env_preserve_keys`, `conditional_secrets`, `smoke`

## Template Safety

1. **Service name mismatches** — if Rakkib renames a dependency container, override the upstream env var in `.env.example`.
2. **Every `${VAR}` in compose** must exist in `.env.example`, come from shell/Docker runtime, or have a safe inline default.
3. **Dynamic values** (generated IDs, ports, UIDs) must be rendered into `docker/<id>/.env` and referenced via `${VAR}`.
4. **`env_preserve_keys`** — add any key written dynamically that should survive re-renders.
5. **Read upstream docs** (`docker-compose.yml`, `.env`, install guide) before finalizing templates; compensate for any divergence.
6. **Verify rendered output**: all inter-container hostnames resolve, no missing vars, service survives `rakkib pull` re-render.

## Registry Fields Checklist

`id` · `state_bucket` · `required`/`optional` · `foundation` (explicit bool) · `image` · `container_name` · `default_port` · `host_service` · `host_port` · `default_subdomain` · `subdomain_key` · `subdomain_placeholder` · `depends_on` · `caddy` (`template`, `public_template`) · `env_keys` · `secrets` · `conditional_secrets` · `postgres` · `monitoring` (`enabled`, `type`, `target`, `path`, `port`, `interval`, `timeout`, `retries`, `hostname`, `custom_url`, `name`) · `homepage` · `data_dirs` · `chown` · `extra_templates` · `hooks` · `env_preserve_keys` · `smoke` (`path`, `expected_text`, optional `timeout`) · `notes`

### Bare-Metal Validation Flow

Validate one new service at a time. Use non-interactive commands whenever possible:

1. Install/update the test server from `main`.
2. Run `rakkib init` when state is missing or intentionally reset.
3. Deploy only the target service with `rakkib pull --service <id>` or `rakkib add <id> --yes`.
4. Confirm the container/host service is running.
5. Run `rakkib smoke <id>` and verify the public URL returns the expected app HTML.
6. Only then move to the next service.

Avoid full `rakkib pull` during service-by-service testing unless intentionally validating the whole selected server. Full pull skips already-running selected services, but it still runs global setup and can expose unrelated state on a reused test server.

## Interview Catalog (`03-services.md`)

- Add service to correct `service_catalog` section with unique numeric alias
- Update `fields.optional_services` or `fields.foundation_services`
- Update "Present This Menu" checklist text
- Update `subdomains:` example and placeholder mapping list
- Describe host-backed services accurately (not as containerized)

## Verification Checklist

1. All referenced template paths exist
2. All hook names resolve (`restart`/`remove` hooks not covered by `test_registry_consistency.py` — verify manually)
3. Service discoverable by id in `registry.yaml`
4. Service appears in `rakkib init` via `03-services.md`
5. `rakkib add <id>` has valid bucket, dependencies, and subdomain behavior
6. All inter-container hostnames are valid after any Rakkib renaming
7. Every compose `${VAR}` is sourced from `.env.example`, shell runtime, or intentional inline default
8. Dynamic setup values are persisted to `.env` when later re-renders depend on them
9. Host installer hooks use shared runner or explicitly preserve the noninteractive env
10. Update Phase 3 service catalog tests when services are added or reordered
11. Update `test_registry_consistency.py` only if existing assertions become insufficient
12. Update fixture/snapshot expectations if rendered outputs change materially
13. Declare `smoke.path` and `smoke.expected_text` for browser-facing services so `rakkib smoke <id>` can verify the public page with a GET request
14. For app+volume containers, inspect the image runtime user and add registry `chown` for writable persistent directories when needed
15. Use `rakkib add <id> --yes` for non-interactive add-path validation, then verify deselection/removal separately through the checkbox UI or explicit removal workflow

## Done When

The repo contains the full declarative definition and all referenced assets needed to deploy and cleanly remove the service through the existing pipeline — no ad hoc follow-up edits required.
