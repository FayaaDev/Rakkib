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
- selected optional services
- subdomains
- Cloudflare tunnel strategy
- secret strategy

For Linux, summarize privilege details without exposing internal state names unless the user asks:
- If `privilege_mode` is `sudo`, show `System setup access: admin approval available` and `Privilege handling: Rakkib will use the safest available method during Step 00`.
- If `privilege_mode` is `root`, show `System setup access: agent is running from a root/admin shell` and `Privilege handling: direct root setup, with user-owned files assigned back to the admin user`.
- If `privilege_mode` is `none`, show `System setup access: not available` and `Install impact: Docker/system setup cannot proceed on a fresh Linux machine`.

If `platform` is `linux` and `privilege_mode` is `sudo`, make the summary explicit that Step 00 will either reuse the installed helper immediately or perform one bootstrap trust event to install or unlock it before root-required work continues.

Make it clear in the summary when `architecture` and `LAN IP` were auto-detected from the host.

If `cloudflare.zone_in_cloudflare` is `false`, the summary must explicitly say that the domain still needs Cloudflare zone setup in the intended account and that public DNS routing plus HTTPS verification will remain blocked until that is done.

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
