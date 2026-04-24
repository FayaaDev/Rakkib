# Step 00 — Prerequisites

Install or verify the base tools needed for the rest of the deployment.

## Inputs

- `platform`
- `privilege_mode`
- `docker_installed`

## Actions

1. Verify `curl` is available.
2. On Linux, decide the privilege path before doing any installs:
   - `privilege_mode: sudo` -> run `sudo -v` once after confirmation and reuse it for the rest of Step 00.
   - `privilege_mode: root` -> run system install commands directly.
   - `privilege_mode: none` -> continue only if Docker is already installed and no remaining Step 00 action needs root.
3. Verify `docker` and `docker compose` are available.
4. If Docker is not installed, install Docker Desktop on Mac or Docker Engine + Compose plugin on Linux.
5. Verify the Docker daemon is running.
6. Verify a local host `cloudflared` binary is available. Step 40 uses the host CLI for tunnel login, creation, and DNS routing, so the Docker image alone is not sufficient.
7. If `cloudflared` is missing, install it into `~/.local/bin/cloudflared` without root, then ensure later steps can invoke it either through `PATH` or by absolute path.

## Platform Notes

Linux:
- Prefer Docker Engine with the Compose plugin.
- Docker Engine installation requires a privileged account.
- If `privilege_mode: sudo`, authenticate once with `sudo -v` inside the installer flow instead of asking the user to edit sudoers.
- Do not continue on a fresh Linux machine with `privilege_mode: none` when Docker still needs to be installed.
- Install the host `cloudflared` CLI into `~/.local/bin/cloudflared` if it is missing before continuing to Step 40.
- A portable install path is acceptable. For example, download the matching release archive for `linux-$ARCH`, extract `cloudflared`, place it at `~/.local/bin/cloudflared`, and `chmod 755` it.

Mac:
- Prefer Docker Desktop.
- Ensure file sharing allows `{{DATA_ROOT}}`.
- Install the host `cloudflared` CLI into `~/.local/bin/cloudflared` if it is missing before continuing to Step 40.
- A portable install path is acceptable. For example, download the matching Darwin release for the recorded architecture, place it at `~/.local/bin/cloudflared`, and `chmod 755` it.

## Verify

- `docker --version`
- `docker compose version`
- `docker info`
- `curl --version`
- `cloudflared --version` or `~/.local/bin/cloudflared --version`
