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

## Cloudflare

- `{{TUNNEL_UUID}}`: Cloudflare tunnel UUID
- `{{TUNNEL_CREDS_PATH}}`: absolute path to the tunnel credentials JSON

## Services

- `{{NOCODB_SUBDOMAIN}}`: default `nocodb`
- `{{NOCODB_DB_PASS}}`: NocoDB database password
- `{{NOCODB_ADMIN_PASS}}`: NocoDB admin password
- `{{N8N_SUBDOMAIN}}`: default `n8n`
- `{{N8N_DB_PASS}}`: n8n database password
- `{{N8N_ENCRYPTION_KEY}}`: n8n encryption key, never rotate after first use
- `{{DBHUB_SUBDOMAIN}}`: default `dbhub`
- `{{OPENCLAW_SUBDOMAIN}}`: default `claw`
- `{{CLAW_GATEWAY_PORT}}`: default `18789`
- `{{CLOUDFLARED_METRICS_PORT}}`: default `20241`
- `{{OPENCLAW_VERSION}}`: optional version label for service docs
- `{{POSTGRES_PASSWORD}}`: Postgres superuser password

## Rule

If a template introduces a new placeholder, add it here in the same change.
