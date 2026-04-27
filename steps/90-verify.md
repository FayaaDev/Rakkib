# Step 90 — Verify

Run the final smoke tests for the deployed server.

## Actions

1. Confirm all expected containers are running.
2. Confirm PostgreSQL is accepting connections.
3. Confirm Caddy is serving locally.
4. Confirm the Cloudflare tunnel metrics endpoint is healthy.
5. Run `rakkib doctor` again and resolve any remaining failures.
6. Confirm each selected service responds on its public HTTPS hostname. If `cloudflare.zone_in_cloudflare` is `false`, treat these checks as blocked until the domain is active in the intended Cloudflare account and do not mark the deployment fully complete.
7. Before rendering the generated machine README, derive `{{SERVICE_SUMMARY_LINES}}` from the always-on services plus the selected foundation and optional services.
8. Derive `{{HOST_ADDON_SUMMARY_LINES}}` from `host_addons`; use `- None` when no host addons are selected, and `- VErgo Terminal shell environment` when `vergo_terminal` is selected.
9. Generate `{{DATA_ROOT}}/README.md` from `templates/agent-memory/SERVER_README.md.tmpl`.
10. Create `~/.claude` if needed and append or replace the Rakkib block in `~/.claude/CLAUDE.md` using `templates/agent-memory/CLAUDE.md.tmpl`.
11. If `~/.config/github-copilot/AGENTS.md` or `~/.codex/AGENTS.md` already exist, append or replace the same Rakkib block there too.
12. On Linux, ensure the repo directory and any files created during the install are owned by `{{ADMIN_USER}}`. Use `sudo -n rakkib privileged fix-repo-owner --state .fss-state.yaml --repo-dir <repo_root>` when needed, plus targeted ownership fixes for user-writable files under `{{DATA_ROOT}}`, so later maintenance can run from the normal account.

## Verify

```bash
# Core
docker ps
docker exec postgres pg_isready -U postgres
curl -s http://localhost/health
rakkib doctor
```

```bash
# Foundation Bundle — run each only if the service is in foundation_services
curl -I https://{{NOCODB_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{AUTHENTIK_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{HOMEPAGE_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{UPTIME_KUMA_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{DOCKGE_SUBDOMAIN}}.{{DOMAIN}}/
```

```bash
# Optional Services — run each only if the service is in selected_services
curl -I https://{{N8N_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{DBHUB_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{IMMICH_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{TRANSFER_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{OPENCLAW_SUBDOMAIN}}.{{DOMAIN}}/
curl -I https://{{HERMES_SUBDOMAIN}}.{{DOMAIN}}/
```

```bash
# Agent memory outputs
test -f {{DATA_ROOT}}/README.md
test -f ~/.claude/CLAUDE.md
```

```bash
# Host addons — run only if vergo_terminal is in host_addons
command -v zsh
command -v eza
command -v zoxide
command -v fzf
test -d ~/.zi/bin
test -f ~/.zshrc
test -f ~/.zshenv
test -f ~/.p10k.zsh
zsh -i -c exit
```

```bash
# VErgo Terminal fonts — run platform-specific check only if vergo_terminal is in host_addons
test -f "$HOME/.local/share/fonts/MesloLGS NF Regular.ttf"      # Linux
test -f "$HOME/Library/Fonts/MesloLGS NF Regular.ttf"           # Mac
test -f ~/.wezterm.lua                                           # Mac
```

```bash
# Authentik-specific (only if authentik is in foundation_services)
docker exec authentik-server ak healthcheck
# Confirm Authentik admin UI is reachable
curl -sf https://{{AUTHENTIK_SUBDOMAIN}}.{{DOMAIN}}/-/health/ready/
# Confirm blueprints were applied — check worker logs for blueprint apply messages
docker logs authentik-worker 2>&1 | grep -i blueprint
```
