# Step 40 — Cloudflare

Render and deploy the Cloudflare tunnel after the user confirms the setup.

## Actions

0. If `cloudflare.zone_in_cloudflare` is `false`, stop before any tunnel login or DNS routing work. Help the user finish Cloudflare zone setup first using Cloudflare's docs, then resume this step once the zone is active in the intended account.
1. Confirm the host `cloudflared` CLI is installed and runnable with `cloudflared --version` before doing any tunnel work. If it was installed into `~/.local/bin`, invoke that path directly when the shell `PATH` has not been refreshed yet.
2. Use the recorded Cloudflare connection method:
   - `browser_login`: use `cloudflared tunnel login`. If `cloudflare.headless` is `true`, tell the user to open the printed Cloudflare URL on another device, approve the domain, return to the terminal, and press Enter if prompted. No API token is needed.
   - `api_token`: ask for a temporary Cloudflare API token only now, export it only for the commands that require it, and unset it after Cloudflare work is complete. Do not write the token into `.fss-state.yaml` or rendered files.
   - `existing_tunnel`: prefer the existing credentials and UUID. Use browser login only if needed to repair missing credentials or DNS routes.
3. If `cloudflare.tunnel_strategy` is `new`, first run `cloudflared tunnel list` and look for the recorded `<tunnel_name>`. If it already exists, record its UUID and reuse it instead of creating another tunnel.
4. If no tunnel with that name exists, guide the user through `cloudflared tunnel login` when using browser login, then run `cloudflared tunnel create <tunnel_name>`.
5. If `cloudflare.tunnel_strategy` is `existing`, confirm the tunnel exists and gather its UUID if not already recorded.
6. Create `{{DATA_ROOT}}/data/cloudflared` if needed.
7. Ensure the credentials JSON ends up at the standardized host path `{{TUNNEL_CREDS_HOST_PATH}}`. If the file currently lives elsewhere, copy or move it into place before rendering.
8. Ensure the credentials JSON is readable only by the admin user.
9. Update `.fss-state.yaml` with the final `tunnel_uuid`, `tunnel_creds_host_path`, and `tunnel_creds_container_path`.
10. Render `templates/cloudflared/config.yml.tmpl` into `{{DATA_ROOT}}/data/cloudflared/config.yml`.
11. Render `templates/docker/cloudflared/docker-compose.yml.tmpl` into `{{DATA_ROOT}}/docker/cloudflared/docker-compose.yml`.
12. Create or update DNS routes in Cloudflare for `{{DOMAIN}}`, `*.{{DOMAIN}}`, and `{{SSH_SUBDOMAIN}}.{{DOMAIN}}`.
13. If a temporary API token was used, unset it before continuing.
14. Start the container with `docker compose up -d` from `{{DATA_ROOT}}/docker/cloudflared`.

## Manual Command Pattern

If the zone is not yet in Cloudflare, first help the user complete one of these:

- primary setup (full): `https://developers.cloudflare.com/dns/zone-setups/full-setup/`
- CNAME setup (partial): `https://developers.cloudflare.com/dns/zone-setups/partial-setup/`

Do not run the tunnel DNS route commands until the zone is active in the Cloudflare account that owns the tunnel.

Normal browser-login pattern, using the actual tunnel name from state:

```bash
cloudflared tunnel login
cloudflared tunnel create <tunnel_name>
cloudflared tunnel route dns <tunnel_name> {{DOMAIN}}
cloudflared tunnel route dns <tunnel_name> '*.{{DOMAIN}}'
cloudflared tunnel route dns <tunnel_name> {{SSH_SUBDOMAIN}}.{{DOMAIN}}
```

On a headless server, `cloudflared tunnel login` prints a Cloudflare URL instead of opening a browser. Tell the user to open that URL on a laptop or phone, sign in to Cloudflare, approve the domain, then return to the terminal.

Only use the advanced API token method if `cloudflare.auth_method` is `api_token`:

```bash
read -r -s -p "Cloudflare API token: " CLOUDFLARE_API_TOKEN
export CLOUDFLARE_API_TOKEN
# Run only the Cloudflare commands that require the token.
unset CLOUDFLARE_API_TOKEN
```

Do not store the raw API token in `.fss-state.yaml`, `.env`, rendered compose files, shell history, or documentation outputs.

## Verify

- `cloudflared --version`
- `test -f {{DATA_ROOT}}/data/cloudflared/config.yml`
- `test -f {{TUNNEL_CREDS_HOST_PATH}}`
- `docker ps | grep cloudflared`
- `curl -fsS http://127.0.0.1:{{CLOUDFLARED_METRICS_PORT}}/metrics`
