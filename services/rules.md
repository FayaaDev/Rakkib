# Service Addition Rules (Rakkib)

This is the checklist for adding any new service to Rakkib.

## Non-Negotiables

1. Use the `rakkib-add-service` skill

Follow the workflow in `.opencode/skills/rakkib-add-service/SKILL.md`.

2. Test on the test server (full bare-metal path)

All newly added services MUST be deployed and verified here:

`sshpass -p 'ub' ssh -o StrictHostKeyChecking=accept-new root@174.138.183.153`

Minimum validation steps:
1. `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash`
2. `rakkib init`
3. `rakkib pull`

For iterative wave validation after the server is initialized, test one service at a time:
1. `rakkib pull --service <service>` or `rakkib add <service> --yes`
2. Check the service container/host process and logs
3. `rakkib smoke <service>` for browser-facing services
4. Move to the next service only after the public HTML smoke check passes

Do not treat local runs as proof.

## Required Implementation Shape

- Add a service entry to `src/rakkib/data/registry.yaml`.
- Add templates under `src/rakkib/data/templates/` (as needed):
  - `docker/<service>/.env.example`
  - `docker/<service>/docker-compose.yml.tmpl`
  - `caddy/routes/<service>.caddy.tmpl`
- Add hooks only when required (use `src/rakkib/hooks/services.py`).
- Keep `rakkib add` behavior correct:
  - selectable in the UI
  - deploys cleanly
  - deselection fully purges service resources

## Acceptance Checks (Required)

- Service appears in `rakkib add` selection and can be selected.
- `rakkib pull` completes with the service running.
- Caddy route works as expected (service reachable via its subdomain).
- Browser-facing services declare registry `smoke.path` and `smoke.expected_text`, and `rakkib smoke <service>` passes.
- Deselect/remove path works (containers down, artifacts removed, Postgres resources dropped if declared).
