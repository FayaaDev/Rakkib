# Question File 04 — Cloudflare

**Phase 4 of 6. No writes outside the repo occur during this phase.**

## AgentSchema

```yaml
schema_version: 1
phase: 4
reads_state:
  - server_name
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
  - id: tunnel_strategy
    type: single_select
    prompt: Should Rakkib create a new Cloudflare tunnel for this server, or reuse an existing one? (new/existing)
    canonical_values: [new, existing]
    aliases:
      new: [new]
      existing: [existing, reuse]
    records:
      - cloudflare.tunnel_strategy
  - id: headless
    type: confirm
    when: cloudflare.tunnel_strategy == new
    prompt: When Rakkib reaches the Cloudflare step, it will ask Cloudflare to approve this server. Is this server headless, meaning it has no browser or desktop? (y/n)
    accepted_inputs:
      y: true
      n: false
      yes: true
      no: false
    records:
      - cloudflare.headless
      - cloudflare.auth_method
    derived_value:
      cloudflare.auth_method: browser_login
  - id: accept_browser_login
    type: confirm
    when: cloudflare.tunnel_strategy == new
    prompt: Use this Cloudflare login method? (y/n)
    accepted_inputs:
      y: true
      n: false
      yes: true
      no: false
  - id: advanced_api_token
    type: confirm
    when: cloudflare.tunnel_strategy == new and accept_browser_login == false
    prompt: Do you need the advanced API token method for a headless or automated setup? (y/n)
    accepted_inputs:
      y: true
      n: false
      yes: true
      no: false
    records:
      - cloudflare.auth_method
    value_if_true:
      cloudflare.auth_method: api_token
  - id: existing_tunnel_auth
    type: derived
    when: cloudflare.tunnel_strategy == existing
    value:
      cloudflare.auth_method: existing_tunnel
      cloudflare.headless: null
    records:
      - cloudflare.auth_method
      - cloudflare.headless
  - id: tunnel_name
    type: text
    prompt: "What tunnel name should be used? [default: <server_name>]"
    default_from_state: server_name
    validate:
      non_empty: true
    records:
      - cloudflare.tunnel_name
  - id: ssh_subdomain
    type: text
    prompt: "What subdomain should route to SSH over Cloudflare? [default: ssh]"
    default: ssh
    validate:
      pattern: ^[a-z0-9-]+$
      message: Use lowercase letters, numbers, and hyphens only.
    records:
      - cloudflare.ssh_subdomain
  - id: knows_tunnel_uuid
    type: confirm
    when: cloudflare.tunnel_strategy == existing
    prompt: Do you already know the existing tunnel UUID? (y/n)
    accepted_inputs:
      y: true
      n: false
      yes: true
      no: false
  - id: tunnel_uuid
    type: text
    when: cloudflare.tunnel_strategy == existing and knows_tunnel_uuid == true
    prompt: Existing tunnel UUID?
    validate:
      pattern: ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$
      message: Enter a valid UUID like 123e4567-e89b-12d3-a456-426614174000.
    records:
      - cloudflare.tunnel_uuid
  - id: tunnel_credential_paths
    type: derived
    when: cloudflare.tunnel_uuid is not null
    source: prior_answer
    derive_from: [data_root, cloudflare.tunnel_uuid]
    value:
      cloudflare.tunnel_creds_host_path: "{{data_root}}/data/cloudflared/{{cloudflare.tunnel_uuid}}.json"
      cloudflare.tunnel_creds_container_path: "/home/nonroot/.cloudflared/{{cloudflare.tunnel_uuid}}.json"
    records:
      - cloudflare.tunnel_creds_host_path
      - cloudflare.tunnel_creds_container_path
```

---

## Instructions for the Agent

Ask the questions below in order. Record the answers into `.fss-state.yaml` under the `cloudflare:` section.

This phase only determines the intended Cloudflare setup. It does not create the tunnel yet. Tunnel login, tunnel creation, DNS routing, and credentials placement happen later in `steps/40-cloudflare.md`.

Make it explicit that Step 40 is a blocking handoff. When Rakkib reaches the Cloudflare step, the install will pause until Cloudflare approves the server or the user switches to the advanced temporary API token path.

Do not ask for a Cloudflare API token during the normal flow. The default and recommended path is Cloudflare browser login. On headless servers, `cloudflared tunnel login` prints a URL that the user can open on another device. Tell the user now if they should keep a laptop or phone ready for that Step 40 approval.

---

## Questions to Ask

### Q2 — Tunnel Strategy

`cloudflare.zone_in_cloudflare` was answered in phase 2 (Q2b in `questions/02-identity.md`). This phase assumes it is `true` and skips asking again unless the user said `n`, in which case the agent must explain that tunnel setup cannot proceed until the domain is active in Cloudflare.

Ask: "Should Rakkib create a new Cloudflare tunnel for this server, or reuse an existing one? (new/existing)"

Accepted answers:
- `new`
- `existing`
- `reuse` -> `existing`

### Q3 — Cloudflare Login Method

Only ask this if Q2 was `new`.

Ask: "When Rakkib reaches Step 40, the install will pause while Cloudflare approves this server. Is this server headless, meaning it has no browser or desktop? (y/n)"

Accepted answers: `y` or `n`. Normalize to boolean as `cloudflare.headless`.

If `n`, explain: "Rakkib will use Cloudflare browser login during setup. The install will pause in Step 40 until you finish the Cloudflare approval in this browser. No API token is needed."

If `y`, explain: "Rakkib will show a Cloudflare login link during setup. Keep another signed-in device ready, open that link there, approve the domain, then return here so Step 40 can continue. No API token is needed."

Record `cloudflare.auth_method: browser_login` for both answers.

Then ask: "Use this Cloudflare login method? (y/n)"

Accepted answers: `y` or `n`.

If `y`, continue without asking for any API token. Remind the user that the install cannot continue past Step 40 until Cloudflare approval finishes.

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

Validation: must be a UUID.

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
