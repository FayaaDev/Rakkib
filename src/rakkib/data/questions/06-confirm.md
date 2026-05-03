# Question File 06 — Confirm

**Phase 6 of 6. This is the last phase before any writes outside the repo.**

## AgentSchema

```yaml
schema_version: 1
phase: 6
reads_state:
  - platform
  - arch
  - privilege_mode
  - privilege_strategy
  - data_root
  - server_name
  - domain
  - admin_user
  - admin_email
  - lan_ip
  - tz
  - foundation_services
  - selected_services
  - host_addons
  - subdomains
  - cloudflare.zone_in_cloudflare
  - cloudflare.auth_method
  - cloudflare.headless
  - cloudflare.tunnel_strategy
  - secrets.mode
writes_state:
  - confirmed
fields:
  - id: deployment_summary
    type: summary
    summary_fields:
      - platform
      - arch
      - privilege_mode
      - privilege_strategy
      - data_root
      - server_name
      - domain
      - admin_user
      - admin_email
      - lan_ip
      - tz
      - foundation_services
      - selected_services
      - host_addons
      - subdomains
      - cloudflare.zone_in_cloudflare
      - cloudflare.auth_method
      - cloudflare.headless
      - cloudflare.tunnel_strategy
      - secrets.mode
  - id: confirmed
    type: confirm
    prompt: Proceed with deployment using the above configuration? [y/N]
    accepted_inputs:
      y: true
      n: false
      "yes": true
      "no": false
    records:
      - confirmed
```

---

## Instructions for the Agent

Before asking for confirmation, present a concise summary of the recorded state using user-friendly labels:

- platform
- architecture
- system setup access
- privilege handling
- data root
- server name
- domain
- admin user
- admin email
- LAN IP
- timezone
- foundation bundle services (and any deselected from the default)
- selected optional services
- subdomains
- Cloudflare connection method
- Cloudflare tunnel strategy
- secret strategy

For Linux, summarize privilege details without exposing internal state names unless the user asks:
- If `privilege_mode` is `sudo`, show `System setup access: agent is running as the normal admin user` and `Privilege handling: sudo is requested only for specific setup actions after confirmation`.
- If `privilege_mode` is `root`, show `System setup access: agent is running from a root/admin shell` and `Privilege handling: direct root setup, with user-owned files assigned back to the admin user`; warn that this is intended only for repair/debug sessions.

Make it clear in the summary when `architecture` and `LAN IP` were auto-detected from the host.

If `cloudflare.zone_in_cloudflare` is `false`, the summary must explicitly say that the domain still needs Cloudflare zone setup in the intended account and that public DNS routing plus HTTPS verification will remain blocked until that is done.

For Cloudflare connection method, use friendly wording:
- If `cloudflare.auth_method` is `browser_login` and `cloudflare.headless` is `false`, show `Cloudflare connection: browser login during Step 3; the install will pause until approval finishes; no API token needed`.
- If `cloudflare.auth_method` is `browser_login` and `cloudflare.headless` is `true`, show `Cloudflare connection: login link opened on another device during Step 3; keep a signed-in laptop or phone ready; the install will pause until approval finishes; no API token needed`.
- If `cloudflare.auth_method` is `api_token`, show `Cloudflare connection: advanced temporary API token during Step 3; used only when needed and not stored in state`.
- If `cloudflare.auth_method` is `existing_tunnel`, show `Cloudflare connection: existing tunnel details; Step 3 may still pause if login is needed to repair DNS routes or missing credentials`.

For Cloudflare tunnel strategy, make it clear whether Rakkib will try to reuse an existing tunnel or create a new one after authentication succeeds.

Then ask for one final yes/no confirmation.

---

## Question to Ask

Ask: "Proceed with deployment using the above configuration? [y/N]"

Accepted answers: `y` or `n`.

If `n`, do not execute any step files. Ask the user which phase they want to revisit, update `.fss-state.yaml`, and return to the appropriate question file.

If `y`, set `confirmed: true` and continue to `steps/00-prereqs.md`.

---

## Record in .fss-state.yaml

```yaml
confirmed: true
```
