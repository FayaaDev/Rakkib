# Step 90 — Verify

Run the final smoke tests for the deployed server.

## Actions

1. Confirm all expected containers are running.
2. Confirm PostgreSQL is accepting connections.
3. Confirm Caddy is serving locally.
4. Confirm the Cloudflare tunnel metrics endpoint is healthy.
5. Confirm each selected service responds on its public HTTPS hostname.
6. Generate `{{DATA_ROOT}}/README.md` from `templates/agent-memory/SERVER_README.md.tmpl`.
7. Create `~/.claude` if needed and append or replace the FayaaSRV block in `~/.claude/CLAUDE.md` using `templates/agent-memory/CLAUDE.md.tmpl`.
8. If `~/.config/github-copilot/AGENTS.md` or `~/.codex/AGENTS.md` already exist, append or replace the same FayaaSRV block there too.

## Verify

- `docker ps`
- `docker exec postgres pg_isready -U postgres`
- `curl -s http://localhost/health`
- `curl -I https://{{NOCODB_SUBDOMAIN}}.{{DOMAIN}}/`
- if selected: `curl -I https://{{N8N_SUBDOMAIN}}.{{DOMAIN}}/`
- if selected: `curl -I https://{{DBHUB_SUBDOMAIN}}.{{DOMAIN}}/`
- if selected: `curl -I https://{{OPENCLAW_SUBDOMAIN}}.{{DOMAIN}}/`
- `test -f {{DATA_ROOT}}/README.md`
- `test -f ~/.claude/CLAUDE.md`
