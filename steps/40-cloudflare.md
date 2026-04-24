# Step 40 — Cloudflare

Render and deploy the Cloudflare tunnel after the user confirms the setup.

## Actions

1. If `cloudflare.tunnel_strategy` is `new`, guide the user through:
   `cloudflared tunnel login` and `cloudflared tunnel create <tunnel_name>`.
2. If `cloudflare.tunnel_strategy` is `existing`, confirm the tunnel exists and gather its UUID and credentials path if not already recorded.
3. Ensure the credentials JSON is stored at the chosen path and readable only by the admin user.
4. Update `.fss-state.yaml` with the final `tunnel_uuid` and `tunnel_creds_path`.
5. Render `templates/cloudflared/config.yml.tmpl` into `{{DATA_ROOT}}/data/cloudflared/config.yml`.
6. Render `templates/docker/cloudflared/docker-compose.yml.tmpl` into `{{DATA_ROOT}}/docker/cloudflared/docker-compose.yml`.
7. Create or update DNS routes in Cloudflare for `{{DOMAIN}}`, `*.{{DOMAIN}}`, and `{{cloudflare.ssh_hostname}}.{{DOMAIN}}`.
8. Start the container with `docker compose up -d` from `{{DATA_ROOT}}/docker/cloudflared`.

## Manual Command Pattern

Use the actual tunnel name from state:

```bash
cloudflared tunnel login
cloudflared tunnel create <tunnel_name>
cloudflared tunnel route dns <tunnel_name> {{DOMAIN}}
cloudflared tunnel route dns <tunnel_name> '*.{{DOMAIN}}'
cloudflared tunnel route dns <tunnel_name> {{cloudflare.ssh_hostname}}.{{DOMAIN}}
```

## Verify

- `test -f {{DATA_ROOT}}/data/cloudflared/config.yml`
- `docker ps | grep cloudflared`
- `curl -fsS http://127.0.0.1:20241/metrics`
