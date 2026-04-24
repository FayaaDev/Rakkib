# Step 60 — Services

Deploy the required and selected application services.

## Actions

1. If `secrets.mode` is `generate`, generate and record any still-missing app secrets before rendering:
   - `NOCODB_ADMIN_PASS`
   - `N8N_ENCRYPTION_KEY` if `n8n` is selected and `n8n_mode` is `fresh`
2. Always render and start NocoDB.
3. If `n8n` is selected, render and start n8n.
4. If `dbhub` is selected, render and start DBHub.
5. For each service:
   render `.env` from `.env.example`, render `docker-compose.yml`, render any extra config files the service needs, then run `docker compose up -d`.
6. After each service starts, verify it internally before moving to the next one.

## Service Notes

NocoDB:
- set `NC_DB` to the dedicated Postgres database
- set `NC_PUBLIC_URL` to `https://{{NOCODB_SUBDOMAIN}}.{{DOMAIN}}`

n8n:
- use the official image template in this repo
- preserve `N8N_ENCRYPTION_KEY` if migrating

DBHub:
- render `dbhub.toml`
- default reverse proxy target remains internal on port 8080

## Verify

- `docker ps | grep nocodb`
- `curl -I http://localhost` through Caddy should no longer fail
- if selected: `docker ps | grep n8n`
- if selected: `docker ps | grep dbhub`
