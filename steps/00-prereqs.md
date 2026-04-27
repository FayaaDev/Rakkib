# Step 00 — Prerequisites

Install or verify the base tools needed for the rest of the deployment.

## Inputs

- `platform`
- `privilege_mode`
- `privilege_strategy`
- `docker_installed`

## Actions

1. Verify `curl` is available.
2. On Linux, verify the agent is running as the normal admin user when `privilege_strategy: on_demand` is recorded. Do not restart the full agent as root.
3. Verify `docker` and `docker compose` are available.
4. If Docker is not installed, install Docker by platform:
   - Mac: use the normal Docker Desktop install flow.
   - Linux: on Ubuntu, install Docker Engine with explicit `sudo` commands using Docker's official apt repository instructions. Install `ca-certificates`, `curl`, and `gnupg`; add Docker's GPG key under `/etc/apt/keyrings`; write `/etc/apt/sources.list.d/docker.list`; then install `docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-buildx-plugin`, and `docker-compose-plugin`.
   - If Linux is not Ubuntu, stop and ask the user before continuing because this repo's documented Linux install path is the official Ubuntu Docker Engine method.
5. On Linux, enable and start Docker with `sudo`, add `{{ADMIN_USER}}` to the `docker` group if that user exists, then continue the install as the normal admin user. If group membership changes do not apply to the current shell, use `sudo docker ...` only for the affected verification commands or ask the user to start a new login session before continuing.
6. Verify the Docker daemon is running.
7. Verify a local host `cloudflared` binary is available. Step 40 uses the host CLI for tunnel login, creation, and DNS routing, so the Docker image alone is not sufficient.
8. If `cloudflared` is missing, install it into the admin user's `~/.local/bin/cloudflared` without requiring a system package, then ensure later steps can invoke it either through `PATH` or by absolute path.
9. Run `rakkib doctor --json` from the repo root after prerequisites are available. Stop on any check with `"status":"fail"`; treat warnings as advisory unless they invalidate the selected install path.

## Platform Notes

Linux:
- Prefer Docker Engine on headless Ubuntu hosts using Docker's official docs: `https://docs.docker.com/engine/install/ubuntu/`
- This documented path assumes Ubuntu and explicit sudo for package/service changes.
- Do not run the full agent as root by default. Use `sudo -n` only for the specific commands that need it so expired authorization fails fast instead of hanging inside the agent session.
- Install the host `cloudflared` CLI into the admin user's `~/.local/bin/cloudflared` if it is missing before continuing to Step 40.
- A portable install path is acceptable. For example, download the matching release archive for `linux-$ARCH`, extract `cloudflared`, place it at `~/.local/bin/cloudflared`, and `chmod 755` it.

Mac:
- Prefer Docker Desktop.
- Ensure file sharing allows `{{DATA_ROOT}}`.
- Install the host `cloudflared` CLI into `~/.local/bin/cloudflared` if it is missing before continuing to Step 40.
- A portable install path is acceptable. For example, download the matching Darwin release for the recorded architecture, place it at `~/.local/bin/cloudflared`, and `chmod 755` it.

## Verify

- Linux: `test "$(id -u)" -ne 0` for the normal user-first flow, or explicitly acknowledge a root repair/debug session
- `docker --version`
- `docker compose version`
- `docker info`
- `curl --version`
- `cloudflared --version` or `~/.local/bin/cloudflared --version`
- `rakkib doctor`
- `rakkib doctor --json`
