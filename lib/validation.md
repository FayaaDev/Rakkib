# Post-Step Validation Checklist

Use these checks after each deployment step. Do not continue if a required check fails.

## Step 00

- Linux helper path: `/usr/local/libexec/fayaasrv-root-helper probe` as root or `sudo -n /usr/local/libexec/fayaasrv-root-helper probe` from a helper-enabled user
- `docker --version`
- `docker compose version`
- `docker info`
- `curl --version`
- `cloudflared --version` or `~/.local/bin/cloudflared --version`

## Step 10

- `ls -ld {{DATA_ROOT}}/docker {{DATA_ROOT}}/data {{DATA_ROOT}}/backups {{DATA_ROOT}}/MDs`
- `test -w {{DATA_ROOT}}/docker`

## Step 20

- `docker network inspect {{DOCKER_NET}}`

## Step 30

- `docker ps | grep caddy`
- `curl -s http://localhost/health`

## Step 40

- `cloudflared --version` or `~/.local/bin/cloudflared --version`
- `test -f {{DATA_ROOT}}/data/cloudflared/config.yml`
- `test -f {{TUNNEL_CREDS_HOST_PATH}}`
- `docker ps | grep cloudflared`
- `curl -fsS http://127.0.0.1:{{CLOUDFLARED_METRICS_PORT}}/metrics`

## Step 50

- `docker ps | grep postgres`
- `docker exec postgres pg_isready -U postgres`
- `docker exec postgres psql -U postgres -c '\l'`
- confirm `nocodb_db` exists
- if selected, confirm `n8n_db` exists

## Step 60

- `docker ps | grep nocodb`
- if selected: `docker ps | grep n8n`
- if selected: `docker ps | grep dbhub`
- local proxy check through Caddy for each selected route

## Step 70

- `node --version`
- `npm --version`
- `test -x "$HOME/.local/bin/openclaw"`
- `"$HOME/.local/bin/openclaw" --version`
- Linux: `systemctl --user status openclaw-gateway.service --no-pager`
- Mac: `launchctl print gui/$(id -u)/openclaw-gateway`
- `curl -I http://localhost:{{CLAW_GATEWAY_PORT}}/`

## Step 80

- `test -x {{BACKUP_DIR}}/backup-local.sh`
- run the script once and confirm a new backup directory exists

## Step 85

- `crontab -l`
- run the installed health check scripts manually once

## Step 90

- `docker ps`
- `docker exec postgres pg_isready -U postgres`
- `curl -s http://localhost/health`
- `curl -I https://{{NOCODB_SUBDOMAIN}}.{{DOMAIN}}/`
- if selected: `curl -I https://{{N8N_SUBDOMAIN}}.{{DOMAIN}}/`
- if selected: `curl -I https://{{DBHUB_SUBDOMAIN}}.{{DOMAIN}}/`
- if selected: `curl -I https://{{OPENCLAW_SUBDOMAIN}}.{{DOMAIN}}/`
- `test -f {{DATA_ROOT}}/README.md`
- `test -f ~/.claude/CLAUDE.md`
