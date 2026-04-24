# Step 30 — Caddy

Render and deploy the base Caddy reverse proxy.

## Actions

1. Render `templates/caddy/Caddyfile.header.tmpl`.
2. Render `templates/caddy/routes/root.caddy.tmpl`.
3. Always render `templates/caddy/routes/nocodb.caddy.tmpl`.
4. Render `templates/caddy/routes/n8n.caddy.tmpl` only if `n8n` is selected.
5. Render `templates/caddy/routes/dbhub.caddy.tmpl` only if `dbhub` is selected.
6. Render `templates/caddy/routes/claw.caddy.tmpl` only if `openclaw` is selected.
7. Render `templates/caddy/Caddyfile.footer.tmpl`.
8. Concatenate the pieces into `{{DATA_ROOT}}/docker/caddy/Caddyfile`.
9. Render `templates/docker/caddy/docker-compose.yml.tmpl` into `{{DATA_ROOT}}/docker/caddy/docker-compose.yml`.
10. Start the container with `docker compose up -d` from `{{DATA_ROOT}}/docker/caddy`.

## Notes

- The root route is intentionally generic for v1. It confirms the server is up even if the user has no landing page yet.
- Host services such as OpenClaw must reverse proxy to `{{HOST_GATEWAY}}`, not the public domain.

## Verify

- `docker ps | grep caddy`
- `curl -s http://localhost/health`
- `docker logs --tail 50 caddy`
