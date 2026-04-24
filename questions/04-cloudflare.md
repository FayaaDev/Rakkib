# Question File 04 — Cloudflare

**Phase 4 of 6. No writes outside the repo occur during this phase.**

---

## Instructions for the Agent

Ask the questions below in order. Record the answers into `.fss-state.yaml` under the `cloudflare:` section.

This phase only determines the intended Cloudflare setup. It does not create the tunnel yet. Tunnel login, tunnel creation, DNS routing, and credentials placement happen later in `steps/40-cloudflare.md`.

---

## Questions to Ask

### Q1 — Zone Ownership

Ask: "Is your base domain already managed in Cloudflare in the same account you will use for this server? (y/n)"

Accepted answers: `y` or `n`. Normalize to boolean.

If `n`, the agent must warn that deployment can continue locally, but external HTTPS verification cannot pass until the domain is moved to or connected through Cloudflare.

### Q2 — Tunnel Strategy

Ask: "Will you create a new Cloudflare tunnel for this server, or reuse an existing one? (new/existing)"

Accepted answers:
- `new`
- `existing`

### Q3 — Tunnel Name

Ask: "What tunnel name should be used? [default: <server_name>]"

If the user gives an empty answer, use `server_name` from `.fss-state.yaml`.

Validation: non-empty.

### Q4 — SSH Hostname

Ask: "What subdomain should route to SSH over Cloudflare? [default: ssh]"

If the user gives an empty answer, use `ssh`.

Validation: lowercase letters, numbers, and hyphens only.

### Q5 — Existing Tunnel Details

Only ask this if Q2 was `existing`.

Ask: "Do you already know the existing tunnel UUID and the credentials JSON path on this machine? (y/n)"

Accepted answers: `y` or `n`.

If `y`, ask:
- "Existing tunnel UUID?"
- "Existing tunnel credentials file path?"

If `n`, record that the values must be gathered during `steps/40-cloudflare.md` before rendering `config.yml`.

---

## Record in .fss-state.yaml

```yaml
cloudflare:
  zone_in_cloudflare: true
  tunnel_strategy: new      # or: existing
  tunnel_name: myserver
  ssh_hostname: ssh
  tunnel_uuid: null
  tunnel_creds_path: null
```

If the user provided the UUID and path, record them instead of `null`.
