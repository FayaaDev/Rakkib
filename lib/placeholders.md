# Placeholder Reference

Every template in this repository uses `{{PLACEHOLDER}}` syntax for direct string substitution by the deployment agent.

## Core

- `{{SERVER_NAME}}`: short machine name used in docs and backup names
- `{{DOMAIN}}`: base domain for the server
- `{{ADMIN_USER}}`: local admin username
- `{{ADMIN_EMAIL}}`: admin email for service bootstrap
- `{{LAN_IP}}`: machine LAN IP for SSH exposure through Cloudflare
- `{{TZ}}`: IANA timezone
- `{{DATA_ROOT}}`: `/srv` on Linux or `$HOME/srv` on Mac by default
- `{{DOCKER_NET}}`: shared Docker network name, default `caddy_net`
- `{{HOST_GATEWAY}}`: host address reachable from containers, `172.18.0.1` on Linux or `host.docker.internal` on Mac
- `{{BACKUP_DIR}}`: default `{{DATA_ROOT}}/backups`
- `{{SERVICE_SUMMARY_LINES}}`: multiline service summary built from the required services plus selected optional services before rendering the generated server README

## Cloudflare

- `{{TUNNEL_UUID}}`: Cloudflare tunnel UUID
- `{{SSH_SUBDOMAIN}}`: SSH subdomain routed through Cloudflare, default `ssh`
- `{{TUNNEL_CREDS_HOST_PATH}}`: standardized host path for the tunnel credentials JSON, `{{DATA_ROOT}}/data/cloudflared/{{TUNNEL_UUID}}.json`
- `{{TUNNEL_CREDS_CONTAINER_PATH}}`: in-container path for the tunnel credentials JSON, `/home/nonroot/.cloudflared/{{TUNNEL_UUID}}.json`

## Services

- `{{NOCODB_SUBDOMAIN}}`: default `nocodb`
- `{{NOCODB_DB_PASS}}`: NocoDB database password
- `{{NOCODB_ADMIN_PASS}}`: NocoDB admin password
- `{{N8N_SUBDOMAIN}}`: default `n8n`
- `{{N8N_DB_PASS}}`: n8n database password
- `{{N8N_ENCRYPTION_KEY}}`: n8n encryption key, never rotate after first use
- `{{DBHUB_SUBDOMAIN}}`: default `dbhub`
- `{{OPENCLAW_SUBDOMAIN}}`: default `claw`
- `{{CLAW_GATEWAY_PORT}}`: default `18789`, derived and recorded before rendering OpenClaw files
- `{{CLOUDFLARED_METRICS_PORT}}`: default `20241`, derived and recorded before rendering Cloudflared files
- `{{POSTGRES_PASSWORD}}`: Postgres superuser password

## Rule

If a template introduces a new placeholder, add it here in the same change.

Render context rule: nested state values must be flattened into these placeholder names before substitution. Do not assume that `subdomains.*` or `secrets.values.*` keys are available to templates directly.
