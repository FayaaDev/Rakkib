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
- whether it needs Authentik integration
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
- `src/rakkib/data/templates/docker/authentik/blueprints/<id>.yaml.tmpl`

Only add the following when required:
- `extra_templates`
- `hooks`
- `postgres` block
- `homepage` block
- `data_dirs`
- `chown`
- `env_preserve_keys`
- `conditional_secrets`

## Registry Checklist

When adding the registry entry, consider:
- `id`
- `state_bucket`
- `required` / `optional`
- `image`
- `container_name` if non-default
- `default_port`
- `host_service`
- `host_port`
- `default_subdomain`
- `subdomain_key`
- `subdomain_placeholder`
- `depends_on`
- `caddy`
- `env_keys`
- `secrets`
- `conditional_secrets`
- `postgres`
- `authentik`
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
2. Confirm every referenced hook name resolves in the hook registries.
3. Confirm the service is discoverable from `registry.yaml` by id.
4. Confirm the service appears in `rakkib init` via `src/rakkib/data/questions/03-services.md`.
5. Confirm `rakkib add <id>` has what it needs:
   - valid bucket
   - valid dependencies
   - valid subdomain behavior
6. Update tests that assert Phase 3 service catalog contents when you add or reorder services.
7. Update `tests/test_registry_consistency.py` only if the existing generic assertions are no longer sufficient.
8. If rendered outputs change materially, update fixture or snapshot expectations.

## Completion Standard

A service addition is only complete when the repo contains the full declarative definition and all referenced assets needed for the service to deploy through the existing pipeline without ad hoc follow-up edits.
