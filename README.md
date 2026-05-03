# Rakkib

Rakkib is a wizard-driven personal server installer. A built-in TUI interview records your answers in `.fss-state.yaml`, renders service templates, and executes verified setup steps to bring up your selected services on a fresh Ubuntu server.

## Quickstart

```bash
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash
```

Then configure and deploy:

```bash
rakkib init   # interview wizard — saves .fss-state.yaml
rakkib pull   # installs prereqs, runs all setup steps
```

For a local clone:

```bash
git clone https://github.com/FayaaDev/Rakkib.git
cd Rakkib
bash install.sh
rakkib init
rakkib pull
```

## How It Works

1. `install.sh` clones or updates the repo, creates a project-local venv at `<repo>/.venv`, installs the rakkib package into it, and symlinks `~/.local/bin/rakkib` onto `PATH`.
2. `rakkib init` runs a TUI interview (phases 1–6) and saves answers to `.fss-state.yaml`. Resumable: re-running picks up from the last incomplete phase.
3. `rakkib pull` reads the confirmed state, installs Docker and cloudflared if missing, then executes setup steps in order — each step runs and verifies before the next begins.
4. `registry.yaml` is the service catalog. Each service entry controls templating, secrets, subdomains, and dependencies.
5. `src/rakkib/data/steps/` contains step modules. Each has `run()` and `verify()` functions; a failed verify halts the installer.

## Commands

```bash
rakkib init              # run the interview wizard
rakkib pull              # install prereqs and apply all steps
rakkib status            # show confirmed state and deployment summary
rakkib add              # sync service selection for an existing deployment
rakkib restart <service> # restart a single deployed service
rakkib restart --all     # restart all services in dependency order
rakkib doctor            # run host diagnostics
rakkib doctor --json     # machine-readable diagnostics output
rakkib doctor --interactive  # diagnostics with guided auto-fix
rakkib auth sudo         # validate sudo for the current terminal
rakkib uninstall         # remove the rakkib CLI shim and PATH entries
```

Root-only helper actions:

```bash
sudo rakkib privileged check
sudo rakkib privileged ensure-layout --state .fss-state.yaml
sudo rakkib privileged fix-repo-owner --state .fss-state.yaml
```

## Services

### Always installed
| Service | Image |
|---------|-------|
| Caddy | `caddy:2` — reverse proxy |
| cloudflared | `cloudflare/cloudflared:latest` — Cloudflare tunnel |
| PostgreSQL | `pgvector/pgvector:pg16` — shared database for all services |

### Foundation bundle (pre-checked, optional)
| Service | Image |
|---------|-------|
| NocoDB | `nocodb/nocodb:latest` — no-code database UI |
| Homepage | `ghcr.io/gethomepage/homepage:latest` — service dashboard |
| Uptime Kuma | `louislam/uptime-kuma:latest` — uptime monitoring |
| Dockge | `louislam/dockge:latest` — Docker Compose manager UI |

### Optional services
| Service | Image |
|---------|-------|
| n8n | `n8nio/n8n:latest` — workflow automation |
| Immich | `ghcr.io/immich-app/immich-server:release` — photo/video library |
| transfer.sh | `dutchcoders/transfer.sh:latest-noroot` — file sharing |
| Jellyfin | `jellyfin/jellyfin:latest` — media server |

## Requirements

- Ubuntu 24.04 is the tested deployment target (macOS supported for development)
- Normal sudo-capable admin user — do not run as root
- A domain on Cloudflare for public HTTPS routes
- Python 3.9+ (the installer handles venv and pip)

## License

See repository for license details.
