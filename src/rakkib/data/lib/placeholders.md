# Placeholder Reference

Every template in this repository uses `{{PLACEHOLDER}}` syntax for direct string substitution by the deployment agent.

## Core

- `{{SERVER_NAME}}`: `server_name`, short machine name used in docs and backup names
- `{{DOMAIN}}`: `domain`, base domain for the server
- `{{ADMIN_USER}}`: `admin_user`, local admin username
- `{{ADMIN_EMAIL}}`: `admin_email`, admin email for service bootstrap
- `{{LAN_IP}}`: `lan_ip`, machine LAN IP for SSH exposure through Cloudflare, auto-detected from the host when possible
- `{{TZ}}`: `tz`, IANA timezone
- `{{DATA_ROOT}}`: `data_root`, `/srv` on Linux or `$HOME/srv` on Mac by default
- `{{DOCKER_NET}}`: `docker_net`, shared Docker network name, default `caddy_net`
- `{{HOST_GATEWAY}}`: `host_gateway`, host address reachable from containers, `172.18.0.1` on Linux or `host.docker.internal` on Mac
- `{{BACKUP_DIR}}`: `backup_dir`, default `{{DATA_ROOT}}/backups`
- `{{SERVICE_SUMMARY_LINES}}`: multiline service summary built from the required services plus selected foundation and optional services before rendering the generated server README
- `{{HOST_ADDON_SUMMARY_LINES}}`: multiline host-addon summary built from `host_addons` before rendering the generated server README

## Cloudflare

- `{{TUNNEL_UUID}}`: `cloudflare.tunnel_uuid`, Cloudflare tunnel UUID
- `{{SSH_SUBDOMAIN}}`: `cloudflare.ssh_subdomain`, SSH subdomain routed through Cloudflare, default `ssh`
- `{{TUNNEL_CREDS_HOST_PATH}}`: `cloudflare.tunnel_creds_host_path`, standardized host path for the tunnel credentials JSON, `{{DATA_ROOT}}/data/cloudflared/{{TUNNEL_UUID}}.json`
- `{{TUNNEL_CREDS_CONTAINER_PATH}}`: `cloudflare.tunnel_creds_container_path`, in-container path for the tunnel credentials JSON, `/home/nonroot/.cloudflared/{{TUNNEL_UUID}}.json`
- `{{CLOUDFLARED_METRICS_PORT}}`: `cloudflared_metrics_port`, default `20241`, derived and recorded before rendering Cloudflared files

## Derived Ports

- `{{CLAW_GATEWAY_PORT}}`: `claw_gateway_port`, default `18789`, derived and recorded before rendering OpenClaw files
- `{{HERMES_DASHBOARD_PORT}}`: `hermes_dashboard_port`, default `9119`, derived and recorded before rendering Hermes files

## Services

### Always installed

- `{{POSTGRES_PASSWORD}}`: `secrets.values.POSTGRES_PASSWORD`, Postgres superuser password

### Foundation Bundle

- `{{NOCODB_SUBDOMAIN}}`: `subdomains.nocodb`, default `nocodb`
- `{{NOCODB_DB_PASS}}`: `secrets.values.NOCODB_DB_PASS`, NocoDB database password
- `{{NOCODB_ADMIN_PASS}}`: `secrets.values.NOCODB_ADMIN_PASS`, NocoDB admin password
- `{{NOCODB_OIDC_CLIENT_ID}}`: `secrets.values.NOCODB_OIDC_CLIENT_ID`, NocoDB OIDC client ID for Authentik; generated during `steps/60-services.md` before rendering the Authentik and NocoDB integration files, then recorded in state
- `{{NOCODB_OIDC_CLIENT_SECRET}}`: `secrets.values.NOCODB_OIDC_CLIENT_SECRET`, NocoDB OIDC client secret for Authentik; generated during `steps/60-services.md` before rendering the Authentik and NocoDB integration files, then recorded in state
- `{{AUTHENTIK_SUBDOMAIN}}`: `subdomains.authentik`, default `auth`
- `{{AUTHENTIK_SECRET_KEY}}`: `secrets.values.AUTHENTIK_SECRET_KEY`, Authentik secret key — random 50-char alphanumeric string, generated once, never rotate
- `{{AUTHENTIK_DB_PASS}}`: `secrets.values.AUTHENTIK_DB_PASS`, Authentik database password
- `{{AUTHENTIK_ADMIN_PASS}}`: `secrets.values.AUTHENTIK_ADMIN_PASS`, Authentik bootstrap admin password; set on first run via `AUTHENTIK_BOOTSTRAP_PASSWORD`
- `{{HOMEPAGE_SUBDOMAIN}}`: `subdomains.homepage`, default `home`
- `{{HOMEPAGE_ALLOWED_HOSTS}}`: rendered from `subdomains.homepage` + `domain`, host validation whitelist for Homepage
- `{{UPTIME_KUMA_SUBDOMAIN}}`: `subdomains.uptime-kuma`, default `status`
- `{{DOCKGE_SUBDOMAIN}}`: `subdomains.dockge`, default `dockge`

### Optional Services

- `{{N8N_SUBDOMAIN}}`: `subdomains.n8n`, default `n8n`
- `{{N8N_DB_PASS}}`: `secrets.values.N8N_DB_PASS`, n8n database password
- `{{N8N_ENCRYPTION_KEY}}`: `secrets.values.N8N_ENCRYPTION_KEY`, n8n encryption key, never rotate after first use
- `{{DBHUB_SUBDOMAIN}}`: `subdomains.dbhub`, default `dbhub`
- `{{IMMICH_SUBDOMAIN}}`: `subdomains.immich`, default `immich`
- `{{IMMICH_DB_PASSWORD}}`: `secrets.values.IMMICH_DB_PASSWORD`, Immich dedicated Postgres password, never rotate after first use
- `{{IMMICH_VERSION}}`: `secrets.values.IMMICH_VERSION`, Immich container tag, default `release`
- `{{TRANSFER_SUBDOMAIN}}`: `subdomains.transfer`, default `transfer`
- `{{OPENCLAW_SUBDOMAIN}}`: `subdomains.openclaw`, default `claw`
- `{{HERMES_SUBDOMAIN}}`: `subdomains.hermes`, default `hermes`

## Rule

If a template introduces a new placeholder, add it here in the same change.

Render context rule: nested state values must be flattened into these placeholder names before substitution. Do not assume that `subdomains.*`, `cloudflare.*`, or `secrets.values.*` keys are available to templates directly.
