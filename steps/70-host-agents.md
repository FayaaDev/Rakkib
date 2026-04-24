# Step 70 — Host Agents

Install host-level services that are not Docker containers.

## Actions

Only run this step if `openclaw` is selected.

Linux:
1. Ensure `node >= 22.14.0` and `npm` are installed. If they are missing, install Node.js 22 LTS first.
2. Install OpenClaw into a user-scoped prefix with `npm install -g --prefix "$HOME/.local" openclaw@latest`.
3. Verify the real entrypoint exists at `~/.local/bin/openclaw` before writing the unit file.
4. Render `templates/systemd/claw-gateway.service.tmpl` into `~/.config/systemd/user/openclaw-gateway.service`.
5. Run `systemctl --user daemon-reload`.
6. Enable and start the service.

Mac:
1. Ensure `node >= 22.14.0` and `npm` are installed. If they are missing, install Node.js 22 LTS first, preferably with Homebrew.
2. Install OpenClaw into a user-scoped prefix with `npm install -g --prefix "$HOME/.local" openclaw@latest`.
3. Verify the real entrypoint exists at `~/.local/bin/openclaw` before writing the plist.
4. Render `templates/launchd/claw-gateway.plist.tmpl` into `~/Library/LaunchAgents/openclaw-gateway.plist`.
5. Load it with `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/openclaw-gateway.plist`.

## Verify

Linux:
- `systemctl --user status openclaw-gateway.service --no-pager`

Mac:
- `launchctl print gui/$(id -u)/openclaw-gateway`

Both:
- `test -x "$HOME/.local/bin/openclaw"`
- `"$HOME/.local/bin/openclaw" --version`
- `curl -I http://localhost:{{CLAW_GATEWAY_PORT}}/`
