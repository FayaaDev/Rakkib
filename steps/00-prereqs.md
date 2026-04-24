# Step 00 — Prerequisites

Install or verify the base tools needed for the rest of the deployment.

## Inputs

- `platform`
- `docker_installed`

## Actions

1. Verify `docker`, `docker compose`, and `curl` are available.
2. If Docker is not installed, install Docker Desktop on Mac or Docker Engine + Compose plugin on Linux.
3. Verify the Docker daemon is running.
4. Verify `cloudflared` is available either as a local binary or via the Docker image.

## Platform Notes

Linux:
- Prefer Docker Engine with the Compose plugin.

Mac:
- Prefer Docker Desktop.
- Ensure file sharing allows `{{DATA_ROOT}}`.

## Verify

- `docker --version`
- `docker compose version`
- `docker info`
- `curl --version`
- `cloudflared --version` or `docker pull cloudflare/cloudflared:latest`
