# Question File 04 — Cloudflare

**Phase 4 of 6. No writes outside the repo occur during this phase.**

---

## Instructions for the Agent

Ask the questions below in order. Record the answers into `.fss-state.yaml` under the `cloudflare:` section.

This phase only determines the intended Cloudflare setup. It does not create the tunnel yet. Tunnel login, tunnel creation, DNS routing, and credentials placement happen later in `steps/40-cloudflare.md`.

Do not ask for a Cloudflare API token during the normal flow. The default and recommended path is Cloudflare browser login. On headless servers, `cloudflared tunnel login` prints a URL that the user can open on another device.

---

## Questions to Ask

### Q2 — Tunnel Strategy

`cloudflare.zone_in_cloudflare` was answered in phase 2 (Q2b in `questions/02-identity.md`). This phase assumes it is `true` and skips asking again unless the user said `n`, in which case the agent must explain that tunnel setup cannot proceed until the domain is active in Cloudflare.

Ask: "Should Rakkib create a new Cloudflare tunnel for this server, or reuse an existing one? (new/existing)"

Accepted answers:
- `new`
- `existing`

### Q3 — Cloudflare Login Method

Only ask this if Q2 was `new`.

Ask: "When Rakkib reaches the Cloudflare step, it will ask Cloudflare to approve this server. Is this server headless, meaning it has no browser or desktop? (y/n)"

Accepted answers: `y` or `n`. Normalize to boolean as `cloudflare.headless`.

If `n`, explain: "Rakkib will use Cloudflare browser login during setup. No API token is needed."

If `y`, explain: "Rakkib will show a Cloudflare login link during setup. Open that link on any device where you can sign in to Cloudflare, approve the domain, then return here. No API token is needed."

Record `cloudflare.auth_method: browser_login` for both answers.

Then ask: "Use this Cloudflare login method? (y/n)"

Accepted answers: `y` or `n`.

If `y`, continue without asking for any API token.

If `n`, ask: "Do you need the advanced API token method for a headless or automated setup? (y/n)"

Accepted answers: `y` or `n`.

If `n`, stop and explain that Rakkib needs either Cloudflare login approval or an advanced API token method before it can create tunnels and DNS routes.

If `y`, record `cloudflare.auth_method: api_token` but do not ask for the token during the interview. Tell the user that Step 40 will request a temporary Cloudflare API token only when it is needed, and the token should not be stored in `.fss-state.yaml`.

For existing tunnels, record `cloudflare.auth_method: existing_tunnel` and `cloudflare.headless: null` by default. Step 40 may still need browser login if DNS routes or missing credentials must be repaired.

### Q4 — Tunnel Name

Ask: "What tunnel name should be used? [default: <server_name>]"

If the user gives an empty answer, use `server_name` from `.fss-state.yaml`.

Validation: non-empty.

### Q5 — SSH Hostname

Ask: "What subdomain should route to SSH over Cloudflare? [default: ssh]"

If the user gives an empty answer, use `ssh`.

Validation: lowercase letters, numbers, and hyphens only.

Record this as the SSH subdomain only, not the full hostname.

### Q6 — Existing Tunnel Details

Only ask this if Q2 was `existing`.

Ask: "Do you already know the existing tunnel UUID? (y/n)"

Accepted answers: `y` or `n`.

If `y`, ask:
- "Existing tunnel UUID?"

If `n`, record that the UUID must be gathered during `steps/40-cloudflare.md` before rendering `config.yml`.

Regardless of whether the tunnel is new or existing, the final credentials file location must always be normalized during `steps/40-cloudflare.md` to:

- host path: `{{DATA_ROOT}}/data/cloudflared/<tunnel_uuid>.json`
- container path: `/home/nonroot/.cloudflared/<tunnel_uuid>.json`

---

## Record in .fss-state.yaml

```yaml
cloudflare:
  zone_in_cloudflare: true    # answered in phase 2 (Q2b in 02-identity.md)
  auth_method: browser_login # browser_login | api_token | existing_tunnel
  headless: false            # true | false | null for existing_tunnel
  tunnel_strategy: new       # or: existing
  tunnel_name: myserver
  ssh_subdomain: ssh
  tunnel_uuid: null
  tunnel_creds_host_path: null
  tunnel_creds_container_path: null
```

If the user provided the UUID, record it and derive the two credentials paths immediately. Otherwise leave them as `null` until `steps/40-cloudflare.md`.
