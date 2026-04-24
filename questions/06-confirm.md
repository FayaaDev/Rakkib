# Question File 06 — Confirm

**Phase 6 of 6. This is the last phase before any writes outside the repo.**

---

## Instructions for the Agent

Before asking for confirmation, present a concise summary of the recorded state:

- platform
- architecture
- privilege mode
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

If `platform` is `linux` and `privilege_mode` is `sudo`, make the summary explicit that the installer will ask for one sudo authentication during Step 00 for system-level setup.

Make it clear in the summary when `architecture` and `LAN IP` were auto-detected from the host.

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
