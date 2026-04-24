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
2. Ubuntu 24.04 run with optional `n8n` and `dbhub` enabled.
3. Ubuntu 24.04 run with `openclaw` enabled, if OpenClaw remains in v1.

## Report Template

| Date | Platform | Selected Services | Result | Blockers Found | Fixes Applied |
|------|----------|-------------------|--------|----------------|---------------|
| pending | pending | pending | pending | pending | pending |

## Status

No dry runs recorded yet.

Required before public release:

- one passing fresh Ubuntu 24.04 baseline run
- one passing fresh Ubuntu 24.04 run with `n8n` and `dbhub`
- one passing fresh Ubuntu 24.04 run with `openclaw`, if OpenClaw remains in v1
