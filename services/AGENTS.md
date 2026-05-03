# Services Workspace — Agent Rules (Rakkib)

This folder is where service names/lists get turned into real, deployable Rakkib services.

## Mission

When OpenCode is launched inside `Rakkib/services`, the user can:
- mention a service name (example: "Vaultwarden", "File Browser"), or
- reference a list file here (example: `batch1.md`, `batchx.md`, `MoreServices/*.md`),
and the agent implements the service in the Rakkib app (registry + templates + hooks + verification updates).

## Hard Requirements

1. Mandatory test-server validation for EVERY new service

Run deployments on the test server (not this machine):

`sshpass -p 'ub' ssh -o StrictHostKeyChecking=accept-new root@174.138.183.153`

Validation must follow the service-targeted bare-metal flow:
- `curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash`
- deploy only the target service with `rakkib add <service> --yes` or `rakkib add --service <service> --yes`
- continue with the service-specific verification steps below

Do not run `rakkib init` or full `rakkib pull` for normal new-service validation. Avoid redeploying unrelated selected services:
- deploy the target with `rakkib add <service> --yes` or `rakkib add --service <service> --yes`
- verify it with `rakkib smoke <service>`
- confirm container/host status and logs before moving to the next service
- reserve full `rakkib pull` only for explicit whole-server validation; it skips already-running selected services but still runs global setup

2. Mandatory skill usage

You MUST use the project skill `rakkib-add-service` for all service additions:
- Skill path: `.opencode/skills/rakkib-add-service/SKILL.md`

Do not hand-roll the workflow; the skill is the contract for registry fields, templates, hooks, and verification alignment.

## Implementation Rules

- Service additions are registry-driven:
  - `src/rakkib/data/registry.yaml`
  - templates under `src/rakkib/data/templates/`
  - hooks only when necessary in `src/rakkib/hooks/services.py`
- Avoid hardcoded per-service branches in Python unless the behavior cannot be expressed via registry/templates/hooks.
- A service is only "done" if it works with:
  - installer-first validation followed by `rakkib add <service> --yes` or `rakkib add --service <service> --yes`
  - `rakkib add` deselect/removal behavior
  - `rakkib smoke <service>` when it is browser-facing
  - destructive removal on deselect (containers, rendered config, data dirs, generated artifacts, Postgres db/role when declared)

## How To Handle User Requests

- If the user gives a service name: locate it in `batch1.md`, `batchx.md`, or `MoreServices/*.md`.
- If the name is missing/ambiguous: ask for the upstream repo URL and whether it needs Postgres.
