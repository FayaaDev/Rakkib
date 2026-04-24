# AGENT RULES — MiniD (Unified Full-Stack)

**Last Updated**: 2026-04-09 | **Server**: FayaaLink (Beelink mini PC) | **OS User**: `fayaalink` | **IP**: `192.168.0.235` | **Domain**: `fayaa92.sa` | **TZ**: `Asia/Riyadh`

---

## Agent Model
MiniD is the **sole agent** with full-stack authority: Docker (20+ containers), Caddy, Cloudflare Tunnel, Linux host, SSH, Postgres, backups, React/Python/Node apps, build pipelines, and MCP servers.

## Operational Standards
- **Backups first**, prefer reversible steps, one issue at a time, CLI-first with exact commands
- For critical ops: state assumptions → impact/risk → commands → verification → rollback

---

## Filesystem Layout
```
/srv/apps/source/<project>/   # BUILD ZONE — NEVER served
/srv/apps/static/<project>/   # SERVE ZONE — serve only
/srv/docker/<service>/        # INFRA ZONE — compose files, .env
/srv/data/<service>/          # PERSISTENCE ZONE — volumes
/srv/MDs/                     # Documentation
/srv/backups/                 # Backup scripts
```
Deploy: `rsync -a --delete dist/ /srv/apps/static/<project>/`

## Static Deployments
| Directory | Domain | Type |
|-----------|--------|------|
| `drfayaa` | `fayaa92.sa` | Landing page |
| `fayform` | `form.fayaa92.sa` | React SPA |
| `MedDare` | `meddare.fayaa92.sa` | React SPA |
| `dashboards-html` | `dashboards.fayaa92.sa` | Static HTML |

---

## Network Architecture
`Internet → Cloudflare Edge → cloudflared tunnel → Caddy (port 80) → services`
- Docker network: `caddy_default` (172.18.0.0/16) — all services join this network
- Host services accessed via `172.18.0.1`; SSH: local `192.168.0.235` or remote `ssh.fayaa92.sa`
- Caddy: Docker → `reverse_proxy container:port` | Host → `reverse_proxy 172.18.0.1:port` | Static → `file_server`

---

## Key Services
| Service | Container/Port | Subdomain | Compose |
|---------|---------------|-----------|---------|
| Caddy | port 80 | (proxy) | `/srv/docker/caddy/` |
| PostgreSQL | `postgres` / 5432 | — | `/srv/docker/postgres/` |
| n8n | `n8n` / 5678 | `n8n.fayaa92.sa` | `/srv/docker/n8n/` |
| NocoDB | `nocodb` / 8080 | `nocodb.fayaa92.sa` | `/srv/docker/nocodb/` |
| DBHub (MCP) | `dbhub` / 5009 | — | `/srv/docker/dbhub/` |
| AdGuard | `adguard` / 3443 | `adblock.fayaa92.sa` | `/srv/docker/adguard/` |
| SehaRadar | `seha-radar` / 8080 | `seha-radar.fayaa92.sa` | `/srv/docker/SehaRadar/` |
| DashPy | `dashpy` / 8050 | `dashpy.fayaa92.sa` | `/srv/docker/dashpy/` |
| OpenCode | systemd / 4097 | (local only) | `/etc/systemd/system/opencode-serve.service` |
| OpenClaw | systemd / 18789 | `claw.fayaa92.sa` | `~/.openclaw/openclaw.json` |

**DBHub** is the standard MCP for Postgres access (`http://127.0.0.1:5009/mcp`). Keep local-only. Use least-privilege per-database users.

---

## Secrets Management
All secrets in `.env` (chmod 600, gitignored). Never hardcode in `docker-compose.yml`.
Structure per service: `docker-compose.yml`, `.env`, `.env.example`, `.gitignore`
**n8n `N8N_ENCRYPTION_KEY` must never change after first run.**

---

## Health Monitoring & Cron Jobs
| Schedule | Job |
|----------|-----|
| `*/5 * * * *` | OpenCode health check — auto-restarts if down |
| `*/5 * * * *` | Cloudflared tunnel check — restarts after 3 failures |
| `*/5 * * * *` | Claw Gateway health check |
| `*/10 * * * *` | Claw memory alert |
| `*/30 * * * *` | Playwright Chrome zombie check |
| `0 3 * * 0` | Playwright Chrome weekly restart |

OpenCode: `systemctl status opencode-serve` | `sudo systemctl restart opencode-serve`
OpenClaw: `systemctl --user status claw-gateway` | `systemctl --user restart claw-gateway`

---

## Backup Strategy
Manual cloud-only to Google Drive (`amd.fayaa@gmail.com` → `fayaalinkBackup/`).
Covers: `/home/fayaalink`, `/srv/docker/`, Postgres dump, `/srv/data/`, OpenClaw config.
Run: `/srv/backups/backup-to-gdrive.sh`

---

## Key Config Files
`/srv/docker/caddy/Caddyfile` | `/srv/data/cloudflared/config.yml`
`/home/fayaalink/.local/bin/status` — server status summary
Docs: `/srv/MDs/` (network_guide, backup_guide, opencode_server, opencode_n8n, SECRETS_MANAGEMENT, GOOGLE_MCP_SETUP_GUIDE, OPENCLAW_WEBSOCKET_FIX)

---

## Enforcement
**Single-agent system.** All operations flow through MiniD. Violations risk data loss, downtime, or security vulnerabilities.
