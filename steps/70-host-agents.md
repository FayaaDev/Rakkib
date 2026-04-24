# Step 70 — Host Agents

Install host-level services that are not Docker containers.

## Actions

Only run this step if `openclaw` is selected.

Linux:
1. Ensure `node >= 22.14.0` and `npm` are installed.
2. Reuse the helper established in Step 00. If `privilege_mode` is `none` and the helper is not already available while Node.js still needs a system install, stop and tell the user to re-run from a privileged account.
3. If Node.js is missing or too old on Ubuntu 24.04, install Node.js 22 LTS through the helper first:
   `/usr/local/libexec/fayaasrv-root-helper install-nodejs22-ubuntu`
4. Verify `node --version` and `npm --version` before installing OpenClaw.
5. Install OpenClaw into a user-scoped prefix with `npm install -g --prefix "$HOME/.local" openclaw@latest`.
6. Verify the real entrypoint exists at `~/.local/bin/openclaw` before writing the unit file.
7. Render `templates/systemd/claw-gateway.service.tmpl` into `~/.config/systemd/user/openclaw-gateway.service`.
8. Run `systemctl --user daemon-reload`.
9. Enable linger through the helper so the user service survives logout and reboots:
   `/usr/local/libexec/fayaasrv-root-helper enable-linger --admin-user {{ADMIN_USER}}`
10. Enable and start the service.

Mac:
1. Ensure `node >= 22.14.0` and `npm` are installed.
2. If Node.js is missing or too old, install Node.js 22 LTS first with Homebrew:
   `brew install node@22`
3. Verify `node --version` and `npm --version` before installing OpenClaw.
4. Install OpenClaw into a user-scoped prefix with `npm install -g --prefix "$HOME/.local" openclaw@latest`.
5. Verify the real entrypoint exists at `~/.local/bin/openclaw` before writing the plist.
6. Render `templates/launchd/claw-gateway.plist.tmpl` into `~/Library/LaunchAgents/openclaw-gateway.plist`.
7. Load it with `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/openclaw-gateway.plist`.

## Verify

Linux:
- `systemctl --user status openclaw-gateway.service --no-pager`

Mac:
- `launchctl print gui/$(id -u)/openclaw-gateway`

Both:
- `node --version`
- `npm --version`
- `test -x "$HOME/.local/bin/openclaw"`
- `"$HOME/.local/bin/openclaw" --version`
- `curl -I http://localhost:{{CLAW_GATEWAY_PORT}}/`
