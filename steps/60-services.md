# Step 60 — Services

Deploy foundation bundle services and selected optional services.

## Actions

### 60.1 — Generate missing secrets

Before rendering any templates, generate and record into `.fss-state.yaml` any secrets not yet present:

- `POSTGRES_PASSWORD` (if not set)
- `NOCODB_ADMIN_PASS`, `NOCODB_DB_PASS` (if nocodb is in `foundation_services`)
- `AUTHENTIK_SECRET_KEY` — 50-char random alphanumeric, never rotate after first run
- `AUTHENTIK_DB_PASS` (if authentik is in `foundation_services`)
- `AUTHENTIK_ADMIN_PASS` (if authentik is in `foundation_services`)
- `NOCODB_OIDC_CLIENT_ID` — UUID v4 (if both nocodb and authentik are in `foundation_services`)
- `NOCODB_OIDC_CLIENT_SECRET` — 40-char random alphanumeric (if both nocodb and authentik are in `foundation_services`)
- `N8N_ENCRYPTION_KEY` (if n8n is in `selected_services` and `n8n_mode` is `fresh`)
- `N8N_DB_PASS` (if n8n is in `selected_services`)

### 60.2 — Deploy Foundation Bundle

Process services in this order: nocodb → authentik → homepage → uptime-kuma → dockge.
Skip any service not present in `foundation_services`. After each service starts, run its internal verify before proceeding.

#### NocoDB

1. Create postgres database and user:
   ```sql
   CREATE DATABASE nocodb_db;
   CREATE USER nocodb WITH PASSWORD '<NOCODB_DB_PASS>';
   GRANT ALL ON DATABASE nocodb_db TO nocodb;
   ```
2. Render `.env` from `templates/docker/nocodb/.env.example` into `{{DATA_ROOT}}/docker/nocodb/.env`.
   - If `authentik` is also in `foundation_services`, uncomment the four `NC_OIDC_*` lines; otherwise leave them commented.
3. Render `docker-compose.yml` from `templates/docker/nocodb/docker-compose.yml.tmpl`.
4. Run `docker compose up -d`.
5. **Caddy route:** render `templates/caddy/routes/nocodb.caddy.tmpl` (plain reverse_proxy, no forward auth).
6. Verify: `docker ps | grep nocodb` and `curl -sf http://localhost:8080/api/v1/health`.

#### Authentik

1. Create postgres database and user:
   ```sql
   CREATE DATABASE authentik;
   CREATE USER authentik WITH PASSWORD '<AUTHENTIK_DB_PASS>';
   GRANT ALL ON DATABASE authentik TO authentik;
   ```
2. Create data directories:
   ```
   {{DATA_ROOT}}/data/authentik/media
   {{DATA_ROOT}}/data/authentik/custom-templates
   {{DATA_ROOT}}/data/authentik/blueprints/custom
   ```
3. Render blueprints — for each service listed below, render its template and write the output to `{{DATA_ROOT}}/data/authentik/blueprints/custom/`. Only render a blueprint if the corresponding service is selected:
   - `nocodb` in `foundation_services` → render `templates/docker/authentik/blueprints/nocodb.yaml.tmpl`
   - `homepage` in `foundation_services` → render `templates/docker/authentik/blueprints/proxy-homepage.yaml.tmpl`
   - `uptime-kuma` in `foundation_services` → render `templates/docker/authentik/blueprints/proxy-uptime-kuma.yaml.tmpl`
   - `dockge` in `foundation_services` → render `templates/docker/authentik/blueprints/proxy-dockge.yaml.tmpl`
   - `n8n` in `selected_services` → render `templates/docker/authentik/blueprints/proxy-n8n.yaml.tmpl`
4. Render `.env` from `templates/docker/authentik/.env.example` into `{{DATA_ROOT}}/docker/authentik/.env`.
5. Render `docker-compose.yml` from `templates/docker/authentik/docker-compose.yml.tmpl`.
6. Run `docker compose up -d`.
7. Wait for `authentik-server` healthcheck to pass — poll `docker inspect --format '{{.State.Health.Status}}' authentik-server` until it returns `healthy` (retry every 10 s, timeout 3 min).
8. **Caddy route:** render `templates/caddy/routes/authentik.caddy.tmpl`.
9. Verify: `docker ps | grep authentik` and `curl -sf http://authentik-server:9000/-/health/ready/` from within the docker network (or via `docker exec authentik-server ak healthcheck`).

#### Homepage

1. Create config directory: `{{DATA_ROOT}}/data/homepage/config`.
2. Generate `services.yaml`: render `templates/docker/homepage/services.yaml.tmpl` and remove any commented entries for services not selected. Write to `{{DATA_ROOT}}/data/homepage/config/services.yaml`.
3. Render `docker-compose.yml` from `templates/docker/homepage/docker-compose.yml.tmpl`.
4. Run `docker compose up -d`.
5. **Caddy route:**
   - If `authentik` is in `foundation_services`: render `templates/caddy/routes/homepage.caddy.tmpl` (includes `forward_auth` block).
   - Otherwise: render a plain route without `forward_auth` (same pattern as nocodb.caddy.tmpl but pointing to `homepage:3000`).
6. Verify: `docker ps | grep homepage`.

#### Uptime Kuma

1. Create data directory: `{{DATA_ROOT}}/data/uptime-kuma`.
2. Render `docker-compose.yml` from `templates/docker/uptime-kuma/docker-compose.yml.tmpl`.
3. Run `docker compose up -d`.
4. **Caddy route:**
   - If `authentik` is in `foundation_services`: render `templates/caddy/routes/uptime-kuma.caddy.tmpl`.
   - Otherwise: render a plain route pointing to `uptime-kuma:3001`.
5. Verify: `docker ps | grep uptime-kuma`.

#### Dockge

1. Create data directory: `{{DATA_ROOT}}/data/dockge`.
2. Render `.env` from `templates/docker/dockge/.env.example` into `{{DATA_ROOT}}/docker/dockge/.env`.
3. Render `docker-compose.yml` from `templates/docker/dockge/docker-compose.yml.tmpl`.
4. Run `docker compose up -d`.
5. **Caddy route:**
   - If `authentik` is in `foundation_services`: render `templates/caddy/routes/dockge.caddy.tmpl`.
   - Otherwise: render a plain route pointing to `dockge:5001`.
6. Verify: `docker ps | grep dockge`.

### 60.3 — Reload Caddy

After all foundation services have their Caddy routes written, reload Caddy:

```bash
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

Verify: `curl -s http://localhost/health` still returns OK and no Caddy error output.

### 60.4 — Deploy Optional Services

Process in order: n8n → dbhub → openclaw. Skip any not in `selected_services`.
For each: render `.env`, render `docker-compose.yml` (and any extra config files), run `docker compose up -d`, then run the per-service verify. Reload Caddy once after all optional services are deployed.

#### n8n

- Create postgres database and user (`n8n` / `N8N_DB_PASS`).
- Preserve `N8N_ENCRYPTION_KEY` if `.env` already exists on the target.
- Render `templates/caddy/routes/n8n.caddy.tmpl`.
- Verify: `docker ps | grep n8n` and `curl -sf http://localhost:5678/healthz`.

#### DBHub

- Render `dbhub.toml` from `templates/docker/dbhub/dbhub.toml.tmpl`.
- Render `templates/caddy/routes/dbhub.caddy.tmpl`.
- Verify: `docker ps | grep dbhub`.

#### OpenClaw

- Install from npm into `~/.local/bin/openclaw` (requires node ≥ 22.14.0).
- Install and enable the systemd user unit (Linux) or launchd plist (Mac) from `templates/systemd/claw-gateway.service.tmpl` or `templates/launchd/claw-gateway.plist.tmpl`.
- Render `templates/caddy/routes/claw.caddy.tmpl`.
- Verify: `curl -sf http://{{HOST_GATEWAY}}:{{CLAW_GATEWAY_PORT}}/health`.

## Service Notes

NocoDB:
- set `NC_DB` to the dedicated Postgres database
- set `NC_PUBLIC_URL` to `https://{{NOCODB_SUBDOMAIN}}.{{DOMAIN}}`
- OIDC vars are only uncommented when Authentik is also in the foundation bundle

Authentik:
- `AUTHENTIK_BOOTSTRAP_EMAIL` and `AUTHENTIK_BOOTSTRAP_PASSWORD` are used only on first container start; Authentik ignores them on subsequent starts
- The embedded outpost auto-discovers proxy providers; no manual outpost configuration is needed after blueprints are applied
- `AUTHENTIK_COOKIE_DOMAIN` must match the root domain so SSO cookies work across all subdomains

n8n:
- preserve `N8N_ENCRYPTION_KEY` if migrating; never overwrite an existing key

## Verify

- `docker ps | grep nocodb` (if in foundation)
- `docker ps | grep authentik` (if in foundation)
- `docker ps | grep homepage` (if in foundation)
- `docker ps | grep uptime-kuma` (if in foundation)
- `docker ps | grep dockge` (if in foundation)
- `docker exec caddy caddy reload --config /etc/caddy/Caddyfile` returns exit 0
- if selected: `docker ps | grep n8n`
- if selected: `docker ps | grep dbhub`
