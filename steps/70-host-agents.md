# Step 70 — Host Agents

Install host-level services that are not Docker containers.

## Actions

Only run this step if `openclaw` is selected.

Linux:
1. Render `templates/systemd/claw-gateway.service.tmpl` into `~/.config/systemd/user/openclaw-gateway.service`.
2. Run `systemctl --user daemon-reload`.
3. Enable and start the service.

Mac:
1. Render `templates/launchd/claw-gateway.plist.tmpl` into `~/Library/LaunchAgents/openclaw-gateway.plist`.
2. Load it with `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/openclaw-gateway.plist`.

## Verify

Linux:
- `systemctl --user status openclaw-gateway.service --no-pager`

Mac:
- `launchctl print gui/$(id -u)/openclaw-gateway`

Both:
- `curl -I http://localhost:{{CLAW_GATEWAY_PORT}}/`
