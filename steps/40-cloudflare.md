# Step 40 — Cloudflare

Render and deploy the Cloudflare tunnel after the user confirms the setup.

## Actions

1. If `cloudflare.tunnel_strategy` is `new`, guide the user through:
   `cloudflared tunnel login` and `cloudflared tunnel create <tunnel_name>`.
2. If `cloudflare.tunnel_strategy` is `existing`, confirm the tunnel exists and gather its UUID if not already recorded.
3. Create `{{DATA_ROOT}}/data/cloudflared` if needed.
4. Ensure the credentials JSON ends up at the standardized host path `{{TUNNEL_CREDS_HOST_PATH}}`. If the file currently lives elsewhere, copy or move it into place before rendering.
5. Ensure the credentials JSON is readable only by the admin user.
6. Update `.fss-state.yaml` with the final `tunnel_uuid`, `tunnel_creds_host_path`, and `tunnel_creds_container_path`.
7. Render `templates/cloudflared/config.yml.tmpl` into `{{DATA_ROOT}}/data/cloudflared/config.yml`.
8. Render `templates/docker/cloudflared/docker-compose.yml.tmpl` into `{{DATA_ROOT}}/docker/cloudflared/docker-compose.yml`.
9. Create or update DNS routes in Cloudflare for `{{DOMAIN}}`, `*.{{DOMAIN}}`, and `{{SSH_SUBDOMAIN}}.{{DOMAIN}}`.
10. Start the container with `docker compose up -d` from `{{DATA_ROOT}}/docker/cloudflared`.

## Manual Command Pattern

Use the actual tunnel name from state:

```bash
cloudflared tunnel login
cloudflared tunnel create <tunnel_name>
cloudflared tunnel route dns <tunnel_name> {{DOMAIN}}
cloudflared tunnel route dns <tunnel_name> '*.{{DOMAIN}}'
cloudflared tunnel route dns <tunnel_name> {{SSH_SUBDOMAIN}}.{{DOMAIN}}
```

## Verify

- `test -f {{DATA_ROOT}}/data/cloudflared/config.yml`
- `test -f {{TUNNEL_CREDS_HOST_PATH}}`
- `docker ps | grep cloudflared`
- `curl -fsS http://127.0.0.1:{{CLOUDFLARED_METRICS_PORT}}/metrics`
