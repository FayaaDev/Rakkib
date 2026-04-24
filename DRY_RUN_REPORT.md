# Dry Run Report

Use this file to record clean-machine installation runs before calling the repo ready for outside users.

## Release Status

Blocked until the required clean-machine runs below are completed and recorded as passing.

## Required Runs

1. Baseline stack on fresh Ubuntu 24.04:
   - Caddy
   - Cloudflared
   - PostgreSQL
   - NocoDB
   - Run from a normal sudo-capable user account and confirm Step 00 installs or reuses the helper instead of relying on raw `sudo` during later steps
2. Ubuntu 24.04 run with optional `n8n` and `dbhub` enabled.
3. Ubuntu 24.04 run with `openclaw` enabled, if OpenClaw remains in v1.
4. Ubuntu 24.04 run with the helper preinstalled before the agent starts.
5. Ubuntu 24.04 run with the installer launched as root, then switched to helper-based privilege handling.

## Report Template

| Date | Platform | Selected Services | Result | Blockers Found | Fixes Applied |
|------|----------|-------------------|--------|----------------|---------------|
| pending | pending | pending | pending | pending | pending |

## Status

No dry runs recorded yet.

Required before public release:

- one passing fresh Ubuntu 24.04 baseline run
- one passing fresh Ubuntu 24.04 baseline run from a standard `sudo` account that bootstraps the helper without blanket `NOPASSWD`
- one passing fresh Ubuntu 24.04 run with `n8n` and `dbhub`
- one passing fresh Ubuntu 24.04 run with `openclaw`, if OpenClaw remains in v1
- one passing fresh Ubuntu 24.04 run with a preinstalled helper
- one passing fresh Ubuntu 24.04 run launched as root and normalized back to helper-first execution
