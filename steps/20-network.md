# Step 20 — Network

Create the shared Docker network used by the proxy and application containers.

## Actions

1. Create the external bridge network `{{DOCKER_NET}}` if it does not already exist.
2. Do not use per-stack auto-generated networks for the main service-to-proxy path.
3. On Linux, document any firewall exception the user may need for port 80.

## Verify

- `docker network inspect {{DOCKER_NET}}`
