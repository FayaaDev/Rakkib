# Question File 03 — Services

**Phase 3 of 6. No writes outside the repo occur during this phase.**

---

## Instructions for the Agent

Present the service selection menu below. Then ask y/n for each optional service in order. After selections are made, ask the user if they want to customize any subdomains. Record all results into `.fss-state.yaml`. Do not advance to `questions/04-cloudflare.md` until recording is complete.

---

## Present This Service Menu

Display the following to the user verbatim (substituting actual values where noted):

```
=== Service Selection ===

Required services (always installed — no choice needed):
  [✓] Caddy          — reverse proxy
  [✓] Cloudflared    — tunnel to Cloudflare edge
  [✓] PostgreSQL      — shared database backend
  [✓] NocoDB         — no-code database UI  →  nocodb.<domain>

Optional services:
  [ ] n8n            — workflow automation (requires PostgreSQL)   →  n8n.<domain>
  [ ] DBHub          — database browser (requires PostgreSQL)      →  dbhub.<domain>
  [ ] OpenClaw       — AI gateway (host service, not Docker)       →  claw.<domain>
```

Use the actual `domain` value from `.fss-state.yaml` in the subdomain examples.

---

## Questions to Ask

Ask each of the following in order:

1. "Install n8n (workflow automation)? (y/n)"
2. "Install DBHub (database browser)? (y/n)"
3. "Install OpenClaw (AI gateway)? (y/n)"

Accepted answers: `y` or `n`. Re-ask on any other input.

---

## Subdomain Customization

After collecting y/n for all optional services, ask:

"Do you want to customize any subdomains? Default subdomains are: nocodb, n8n, dbhub, claw (for OpenClaw). (y/n)"

If the user answers `y`:
- Ask for each service (required + selected optional): "Subdomain for <service>? [default: <default>]"
- If the user presses enter or provides an empty value, keep the default.

If the user answers `n`, use all defaults.

---

## Record in .fss-state.yaml

```yaml
selected_services: [n8n, dbhub]   # list only those the user selected; omit unselected ones
subdomains:
  nocodb: nocodb                   # always present
  n8n: n8n                         # only if n8n selected
  dbhub: dbhub                     # only if dbhub selected
  claw: claw                       # only if openclaw selected
```

Record customized subdomain values if the user changed any defaults.

During rendering, flatten these values into service placeholders:

- `subdomains.nocodb` -> `{{NOCODB_SUBDOMAIN}}`
- `subdomains.n8n` -> `{{N8N_SUBDOMAIN}}`
- `subdomains.dbhub` -> `{{DBHUB_SUBDOMAIN}}`
- `subdomains.claw` -> `{{OPENCLAW_SUBDOMAIN}}`
