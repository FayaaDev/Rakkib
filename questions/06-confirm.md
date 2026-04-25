# Question File 06 — Confirm

**Phase 6 of 6. This is the last phase before any writes outside the repo.**

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
- LAN IP
- timezone
- foundation bundle services (and any deselected from the default)
- selected optional services
- subdomains
- Cloudflare connection method
- Cloudflare tunnel strategy
- secret strategy

For Linux, summarize privilege details without exposing internal state names unless the user asks:
- If `privilege_mode` is `sudo`, show `System setup access: admin approval available` and `Privilege handling: Rakkib will use the safest available method during Step 00`.
- If `privilege_mode` is `root`, show `System setup access: agent is running from a root/admin shell` and `Privilege handling: direct root setup, with user-owned files assigned back to the admin user`.
- If `privilege_mode` is `none`, show `System setup access: not available` and `Install impact: Docker/system setup cannot proceed on a fresh Linux machine`.

If `platform` is `linux` and `privilege_mode` is `sudo`, make the summary explicit that Step 00 will reuse the installed helper if present. If the helper is absent, the agent should have already instructed a relaunch with `sudo -E <agent>` in Phase 1.

Make it clear in the summary when `architecture` and `LAN IP` were auto-detected from the host.

If `cloudflare.zone_in_cloudflare` is `false`, the summary must explicitly say that the domain still needs Cloudflare zone setup in the intended account and that public DNS routing plus HTTPS verification will remain blocked until that is done.

For Cloudflare connection method, use friendly wording:
- If `cloudflare.auth_method` is `browser_login` and `cloudflare.headless` is `false`, show `Cloudflare connection: browser login during setup; no API token needed`.
- If `cloudflare.auth_method` is `browser_login` and `cloudflare.headless` is `true`, show `Cloudflare connection: login link opened on another device; no API token needed`.
- If `cloudflare.auth_method` is `api_token`, show `Cloudflare connection: advanced temporary API token during Step 40; token will not be stored in state`.
- If `cloudflare.auth_method` is `existing_tunnel`, show `Cloudflare connection: existing tunnel details`.

Then ask for one final yes/no confirmation.

---

## Question to Ask

Ask: "Proceed with deployment using the above configuration? (y/n)"

Accepted answers: `y` or `n`.

If `n`, do not execute any step files. Ask the user which phase they want to revisit, update `.fss-state.yaml`, and return to the appropriate question file.

If `y`, set `confirmed: true` and continue to `steps/00-prereqs.md`.

---

## Record in .fss-state.yaml

```yaml
confirmed: true
```
