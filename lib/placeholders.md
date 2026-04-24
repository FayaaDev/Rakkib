# Placeholder Reference

Every template in this repository uses `{{PLACEHOLDER}}` syntax for find/replace by the deployment agent. This file is the authoritative list of all placeholders used across the codebase.

## Global / Infrastructure

### {{SERVER_NAME}}
**Used in:** 
- `templates/backups/backup-local.sh.tmpl`

**Default/Example:** `myserver`, `prod-srv-01`

**Notes:** Machine hostname for identification in backup manifests and server documentation.

---

### {{DOMAIN}}
**Used in:**
- `templates/cloudflared/config.yml.tmpl`
- `templates/caddy/routes/*.caddy.tmpl`

**Default/Example:** `example.com`, `fayaa92.sa`

**Notes:** Base domain used for all service subdomains. Critical for Cloudflare tunnel ingress routing and Caddy reverse proxy.

---

### {{ADMIN_USER}}
**Used in:**
- `templates/systemd/claw-gateway.service.tmpl`
- `templates/backups/backup-local.sh.tmpl`

**Default/Example:** `ubuntu`, `fayaalink`

**Notes:** Linux admin username used in systemd units and backup script paths.

---

### {{ADMIN_EMAIL}}
**Notes:** Reserved for future use in admin notifications. Currently undocumented in templates; include for completeness.

**Default/Example:** `admin@example.com`, `drfayaa@gmail.com`

---

### {{LAN_IP}}
**Used in:**
- `templates/cloudflared/config.yml.tmpl`

**Default/Example:** `192.168.1.100`, `192.168.0.235`

**Notes:** Local LAN IP address for routing host services (SSH, host-only services) through cloudflared tunnel.

---

### {{TZ}}
**Notes:** Reserved for future use in time-zone-dependent services (n8n, postgres, cron scheduling). Currently undocumented in templates; include for completeness.

**Default/Example:** `America/New_York`, `Asia/Riyadh`

**Notes:** IANA timezone identifier for container environments and scheduled jobs.

---

### {{DATA_ROOT}}
**Used in:**
- `templates/backups/backup-local.sh.tmpl`
- All compose files implicitly (paths referenced in backup script)

**Default/Example:** `/srv` (Linux), `$HOME/srv` (Mac)

**Notes:** Base data path for all persistent storage, docker configs, and backups. Critical for infrastructure layout.

---

### {{DOCKER_NET}}
**Notes:** Reserved for future use in compose files. Currently undocumented in templates; include for completeness.

**Default/Example:** `caddy_default`, `caddy_net`

**Notes:** Docker network name that all services join for inter-container communication.

---

### {{PLATFORM}}
**Notes:** Reserved for future conditional logic in deployment steps. Currently undocumented in templates; include for completeness.

**Default/Example:** `linux`, `mac`

**Notes:** Platform identifier used to branch behavior during deployment (OS-specific paths, commands).

---

## Cloudflare Tunnel

### {{TUNNEL_UUID}}
**Used in:**
- `templates/cloudflared/config.yml.tmpl`

**Default/Example:** `550e8400-e29b-41d4-a716-446655440000`

**Notes:** UUID of the cloudflared tunnel. Generated during `cloudflare tunnel create`. Never rotate—credentials are locked to this UUID.

---

### {{TUNNEL_CREDS_PATH}}
**Used in:**
- `templates/cloudflared/config.yml.tmpl`

**Default/Example:** `/srv/data/cloudflared/credentials.json`

**Notes:** Absolute path to tunnel credentials JSON file. Generated when tunnel is created via `cloudflare tunnel create`.

---

## Backup

### {{BACKUP_DIR}}
**Notes:** Reserved for future use. Currently hardcoded in backup script as `{{DATA_ROOT}}/backups`.

**Default/Example:** `/srv/backups`

**Notes:** Absolute path for backup storage directory.

---

## Per-Service Configuration

### {{NOCODB_SUBDOMAIN}}
**Notes:** Reserved for future use in Caddy routes. Currently undocumented in templates; include for completeness.

**Default/Example:** `nocodb`

**Notes:** Subdomain for NocoDB service. Becomes `nocodb.{{DOMAIN}}` in Caddy routing.

---

### {{NOCODB_DB_PASS}}
**Notes:** Reserved for future use in nocodb compose/environment. Currently undocumented in templates; include for completeness.

**Default/Example:** Generated strong password (32+ chars)

**Notes:** PostgreSQL password for nocodb database user. Store securely in `.env`.

---

### {{NOCODB_ADMIN_PASS}}
**Notes:** Reserved for future use in nocodb compose/environment. Currently undocumented in templates; include for completeness.

**Default/Example:** Generated strong password (32+ chars)

**Notes:** NocoDB admin account password. Store securely in `.env`.

---

### {{N8N_SUBDOMAIN}}
**Notes:** Reserved for future use in Caddy routes. Currently undocumented in templates; include for completeness.

**Default/Example:** `n8n`

**Notes:** Subdomain for n8n service. Becomes `n8n.{{DOMAIN}}` in Caddy routing.

---

### {{N8N_DB_PASS}}
**Notes:** Reserved for future use in n8n compose/environment. Currently undocumented in templates; include for completeness.

**Default/Example:** Generated strong password (32+ chars)

**Notes:** PostgreSQL password for n8n database user. Store securely in `.env`.

---

### {{N8N_ENCRYPTION_KEY}}
**Notes:** Reserved for future use in n8n compose/environment. Currently undocumented in templates; include for completeness.

**Default/Example:** Generated via `openssl rand -base64 32`

**Notes:** n8n encryption key for sensitive data. **CRITICAL: Generate once and NEVER rotate.** Rotation breaks all encrypted credentials in n8n.

---

### {{DBHUB_SUBDOMAIN}}
**Notes:** Reserved for future use in Caddy routes. Currently undocumented in templates; include for completeness.

**Default/Example:** `dbhub`

**Notes:** Subdomain for dbhub service.

---

### {{OPENCLAW_SUBDOMAIN}}
**Notes:** Reserved for future use in Caddy routes. Currently undocumented in templates; include for completeness.

**Default/Example:** `claw`

**Notes:** Subdomain for OpenClaw service. Becomes `claw.{{DOMAIN}}` in Caddy routing.

---

### {{CLAW_GATEWAY_PORT}}
**Used in:**
- `templates/systemd/claw-gateway.service.tmpl`

**Default/Example:** `18789`

**Notes:** Port for OpenClaw gateway systemd service. Must not conflict with other services.

---

### {{OPENCODE_PORT}}
**Used in:**
- `templates/backups/healthchecks/opencode-healthcheck.sh.tmpl`

**Default/Example:** `4097`

**Notes:** Port for OpenCode service health checks. Used in monitoring/healthcheck scripts.

---

### {{CLOUDFLARED_METRICS_PORT}}
**Used in:**
- `templates/backups/healthchecks/cloudflared-healthcheck.sh.tmpl`

**Default/Example:** `5555`

**Notes:** Port for cloudflared metrics endpoint. Used for tunnel monitoring and health checks.

---

### {{OPENCLAW_VERSION}}
**Used in:**
- `templates/systemd/claw-gateway.service.tmpl`

**Default/Example:** `1.0.0`, `latest`

**Notes:** Version tag for OpenClaw service. Used in systemd unit description and environment variable for service introspection.

---

### {{POSTGRES_PASSWORD}}
**Notes:** Reserved for future use in postgres compose/environment. Currently undocumented in templates; include for completeness.

**Default/Example:** Generated strong password (32+ chars)

**Notes:** PostgreSQL superuser password. Store securely in `.env`. All services authenticate via their own database users with scoped permissions.

---

## Summary

**Total unique placeholders:** 17

**Found in templates via grep:** 17

**Per-service pattern:** `{{<SVC>_SUBDOMAIN}}`, `{{<SVC>_DB_PASS}}`

**Reserved (not yet in templates):** `{{PLATFORM}}`, `{{DOCKER_NET}}`, `{{ADMIN_EMAIL}}`, `{{TZ}}`, `{{BACKUP_DIR}}`, `{{DBHUB_SUBDOMAIN}}`, `{{N8N_SUBDOMAIN}}`, `{{N8N_DB_PASS}}`, `{{N8N_ENCRYPTION_KEY}}`, `{{NOCODB_SUBDOMAIN}}`, `{{NOCODB_DB_PASS}}`, `{{NOCODB_ADMIN_PASS}}`, `{{POSTGRES_PASSWORD}}`
