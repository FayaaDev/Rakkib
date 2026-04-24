# Step 00 — Prerequisites

Install or verify the base tools needed for the rest of the deployment.

## Inputs

- `platform`
- `docker_installed`

## Actions

1. Verify `docker`, `docker compose`, and `curl` are available.
2. If Docker is not installed, install Docker Desktop on Mac or Docker Engine + Compose plugin on Linux.
3. Verify the Docker daemon is running.
4. Verify a local host `cloudflared` binary is available. Step 40 uses the host CLI for tunnel login, creation, and DNS routing, so the Docker image alone is not sufficient.

## Platform Notes

Linux:
- Prefer Docker Engine with the Compose plugin.
- Install the host `cloudflared` package if it is missing before continuing to Step 40.

Mac:
- Prefer Docker Desktop.
- Ensure file sharing allows `{{DATA_ROOT}}`.
- Install the host `cloudflared` binary, for example with Homebrew, if it is missing before continuing to Step 40.

## Verify

- `docker --version`
- `docker compose version`
- `docker info`
- `curl --version`
- `cloudflared --version`
