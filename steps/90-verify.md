# Step 90 — Verify

Run the final smoke tests for the deployed server.

## Actions

1. Confirm all expected containers are running.
2. Confirm PostgreSQL is accepting connections.
3. Confirm Caddy is serving locally.
4. Confirm the Cloudflare tunnel metrics endpoint is healthy.
5. Confirm each selected service responds on its public HTTPS hostname.
6. Generate `{{DATA_ROOT}}/README.md` from `templates/agent-memory/SERVER_README.md.tmpl`.
7. Append or create the local agent memory file from `templates/agent-memory/CLAUDE.md.tmpl`.

## Verify

- `docker ps`
- `docker exec postgres pg_isready -U postgres`
- `curl -s http://localhost/health`
- `curl -I https://{{NOCODB_SUBDOMAIN}}.{{DOMAIN}}/`
- if selected: `curl -I https://{{N8N_SUBDOMAIN}}.{{DOMAIN}}/`
- if selected: `curl -I https://{{DBHUB_SUBDOMAIN}}.{{DOMAIN}}/`
- if selected: `curl -I https://{{OPENCLAW_SUBDOMAIN}}.{{DOMAIN}}/`
- `test -f {{DATA_ROOT}}/README.md`
