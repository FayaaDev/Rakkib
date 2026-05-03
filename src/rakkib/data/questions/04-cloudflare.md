# Question File 04 — Cloudflare

**Phase 4 of 6. No writes outside the repo occur during this phase.**

## AgentSchema

```yaml
schema_version: 1
phase: 4
reads_state:
  - server_name
  - admin_user
  - data_root
  - cloudflare.zone_in_cloudflare
writes_state:
  - cloudflare.auth_method
  - cloudflare.headless
  - cloudflare.tunnel_strategy
  - cloudflare.tunnel_name
  - cloudflare.ssh_subdomain
  - cloudflare.tunnel_uuid
  - cloudflare.tunnel_creds_host_path
  - cloudflare.tunnel_creds_container_path
fields:
  - id: cloudflare_defaults
    type: derived
    value:
      cloudflare.auth_method: browser_login
      cloudflare.headless: true
      cloudflare.tunnel_strategy: new
      cloudflare.tunnel_name: "{{admin_user}}-tunnel"
      cloudflare.ssh_subdomain: ssh
      cloudflare.tunnel_uuid: null
      cloudflare.tunnel_creds_host_path: null
      cloudflare.tunnel_creds_container_path: null
    records:
      - cloudflare.auth_method
      - cloudflare.headless
      - cloudflare.tunnel_strategy
      - cloudflare.tunnel_name
      - cloudflare.ssh_subdomain
      - cloudflare.tunnel_uuid
      - cloudflare.tunnel_creds_host_path
      - cloudflare.tunnel_creds_container_path
```

---

## Instructions for the Agent

This phase records the intended Cloudflare setup into `.fss-state.yaml` under the `cloudflare:` section.

This phase only determines the intended Cloudflare setup. It does not create the tunnel yet. Tunnel login, tunnel creation, DNS routing, and credentials placement happen later in `steps/3-cloudflare.md`.

Make it explicit that Step 3 is a blocking handoff. When Rakkib reaches the Cloudflare step, the install will pause until Cloudflare approves the server.

Do not ask for a Cloudflare API token during the normal flow. The default and recommended path is Cloudflare browser login. On headless servers, `cloudflared tunnel login` prints a URL that the user can open on another device.

---

## Questions to Ask

None. This phase is fully automatic:

- Always create a new tunnel (`cloudflare.tunnel_strategy: new`).
- Always use Cloudflare browser login during Step 3 (`cloudflare.auth_method: browser_login`).
- Assume headless and show the login link flow during Step 3 (`cloudflare.headless: true`).
- Tunnel name is derived from the admin username (`{{admin_user}}-tunnel`).
- SSH subdomain is always `ssh`.

---

## Record in .fss-state.yaml

```yaml
cloudflare:
  zone_in_cloudflare: true    # answered in phase 2 (Q2b in 02-identity.md)
  auth_method: browser_login
  headless: true
  tunnel_strategy: new
  tunnel_name: "<admin_user>-tunnel"
  ssh_subdomain: ssh
  tunnel_uuid: null
  tunnel_creds_host_path: null
  tunnel_creds_container_path: null
```

If the user provided the UUID, record it and derive the two credentials paths immediately. Otherwise leave them as `null` until `steps/40-cloudflare.md`.
