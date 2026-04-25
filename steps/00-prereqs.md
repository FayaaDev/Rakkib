# Step 00 — Prerequisites

Install or verify the base tools needed for the rest of the deployment.

## Inputs

- `platform`
- `privilege_mode`
- `privilege_strategy`
- `helper.installed`
- `helper.version`
- `helper.bootstrap_required`
- `docker_installed`

## Actions

1. Verify `curl` is available.
2. On Linux, detect whether root-required actions are still needed for this machine. At minimum, treat Docker Engine installation, `/srv` creation, Ubuntu Node.js installation for OpenClaw, and linger setup as helper-scoped work.
3. On Linux, probe the helper before doing any root-required install work:
   - helper already usable -> record its version and continue with helper verbs only.
   - helper absent and `privilege_mode: root` -> run `./scripts/install-privileged-helper --admin-user {{ADMIN_USER}}` directly (no `sudo` prefix), then continue through the helper. The script will chown the repo back to `{{ADMIN_USER}}` after installing the helper.
   - helper absent and `privilege_mode: sudo` -> this state should not normally occur because Phase 1 instructs the user to relaunch with `sudo -E <agent>` when unprivileged. As a guardrail, print the relaunch instruction using the agent's absolute path and stop. Do not print a manual command to run in another terminal.
   - helper absent and `privilege_mode: none` -> continue only if Docker is already installed and no remaining Step 00 action needs root; otherwise stop.
4. Verify `docker` and `docker compose` are available.
5. If Docker is not installed, install Docker by platform:
   - Mac: use the normal Docker Desktop install flow.
   - Linux: on Ubuntu, call `/usr/local/libexec/rakkib-root-helper install-docker-engine-ubuntu --admin-user {{ADMIN_USER}}`. This reviewed path also installs `acl` so the helper can use `setfacl` for the same-session Docker socket bridge.
   - If Linux is not Ubuntu, stop and ask the user before continuing because this repo's documented Linux install path is the official Ubuntu Docker Engine method.
6. Verify the Docker daemon is running.
7. Do not leave Step 00 until the current installer session can run plain `docker` commands successfully. If the helper added the admin user to the `docker` group and had to bridge immediate socket access for the current session, verify that bridge now instead of scattering raw `sudo docker ...` later. If the helper reports `docker_socket_acl_applied: false`, stop and require a session refresh or explicit fallback before continuing.
8. Verify a local host `cloudflared` binary is available. Step 40 uses the host CLI for tunnel login, creation, and DNS routing, so the Docker image alone is not sufficient.
9. If `cloudflared` is missing, install it into `~/.local/bin/cloudflared` without root, then ensure later steps can invoke it either through `PATH` or by absolute path.

## Platform Notes

Linux:
- Prefer Docker Engine on headless Ubuntu hosts using Docker's official docs: `https://docs.docker.com/engine/install/ubuntu/`
- This documented path assumes Ubuntu and a helper-capable privileged account.
- Bootstrap installs must go through `scripts/install-privileged-helper`, which creates the root-owned helper at `/usr/local/libexec/rakkib-root-helper` and the scoped `/etc/sudoers.d/rakkib-helper` entry for that path only.
- Do not continue on a fresh Linux machine with `privilege_mode: none` when Docker still needs to be installed and no helper is already available.
- The helper is responsible for the reviewed Ubuntu Docker Engine path, including installing `acl`, adding `{{ADMIN_USER}}` to the `docker` group, and handling the minimum temporary bridge needed for the current installer session to run `docker` immediately after install.
- Install the host `cloudflared` CLI into `~/.local/bin/cloudflared` if it is missing before continuing to Step 40.
- A portable install path is acceptable. For example, download the matching release archive for `linux-$ARCH`, extract `cloudflared`, place it at `~/.local/bin/cloudflared`, and `chmod 755` it.

Mac:
- Prefer Docker Desktop.
- Ensure file sharing allows `{{DATA_ROOT}}`.
- Install the host `cloudflared` CLI into `~/.local/bin/cloudflared` if it is missing before continuing to Step 40.
- A portable install path is acceptable. For example, download the matching Darwin release for the recorded architecture, place it at `~/.local/bin/cloudflared`, and `chmod 755` it.

## Verify

- Linux helper path: `/usr/local/libexec/rakkib-root-helper probe` as root or `sudo -n /usr/local/libexec/rakkib-root-helper probe` from a helper-enabled user
- `docker --version`
- `docker compose version`
- `docker info`
- `curl --version`
- `cloudflared --version` or `~/.local/bin/cloudflared --version`
