# Question File 03 — Services

**Phase 3 of 6. No writes outside the repo occur during this phase.**

---

## Instructions for the Agent

Present the full service menu below as a TUI-style checklist. Collect selections in two rounds:
1. **Foundation Bundle** — all pre-selected; user types numbers to deselect.
2. **Optional Services** — none pre-selected; user types numbers to select.

After both rounds, offer subdomain customization. Record all results into `.fss-state.yaml`. Do not advance to `questions/04-cloudflare.md` until recording is complete.

---

## Present This Menu

Display the following to the user (substituting the actual `domain` value from `.fss-state.yaml`):

```
=== Service Selection ===

Always installed — no choice needed:
  [✓] Caddy          — reverse proxy
  [✓] Cloudflared    — tunnel to Cloudflare edge
  [✓] PostgreSQL     — shared database backend

Foundation Bundle (recommended):
  [✓] 1  NocoDB        — no-code database UI    →  nocodb.<domain>
  [✓] 2  Authentik     — SSO / auth proxy       →  auth.<domain>
  [✓] 3  Homepage      — service dashboard      →  home.<domain>
  [✓] 4  Uptime Kuma   — uptime monitoring      →  status.<domain>
  [✓] 5  Dockge        — Compose manager        →  dockge.<domain>

Optional Services:
  [ ] 6  n8n           — workflow automation    →  n8n.<domain>
  [ ] 7  DBHub         — database browser       →  dbhub.<domain>
  [ ] 8  OpenClaw      — AI gateway             →  claw.<domain>
```

---

## Round 1 — Foundation Bundle

Ask:

> "Foundation Bundle: type numbers to deselect (e.g. `3 5`), or press Enter to accept all:"

- Parse the response as a space-separated list of integers.
- Remove the corresponding services from the selected foundation set.
- If the user presses Enter with no input, keep all five selected.
- Re-render the updated checklist showing `[✓]` / `[ ]` states and ask the user to confirm.

---

## Round 2 — Optional Services

Ask:

> "Optional Services: type numbers to add (e.g. `6 8`), or press Enter to skip all:"

- Parse the response as a space-separated list of integers (6–8).
- Add the corresponding services to the selection.
- If the user presses Enter with no input, none are selected.

---

## Subdomain Customization

After both rounds, ask:

> "Do you want to customize any subdomains? Defaults: nocodb, auth, home, status, dockge, n8n, dbhub, claw. (y/n)"

If `y`:
- For each selected service (foundation + optional), ask: "Subdomain for `<service>`? [default: `<default>`]"
- Empty input keeps the default.

If `n`, use all defaults.

---

## Record in .fss-state.yaml

```yaml
foundation_services:            # list only those kept from the foundation bundle
  - nocodb
  - authentik
  - homepage
  - uptime-kuma
  - dockge
selected_services:              # list only those the user added from optional services
  - n8n
subdomains:
  nocodb: nocodb                 # always present if nocodb is in foundation_services
  auth: auth                     # always present if authentik is in foundation_services
  home: home                     # always present if homepage is in foundation_services
  status: status                 # always present if uptime-kuma is in foundation_services
  dockge: dockge                 # always present if dockge is in foundation_services
  n8n: n8n                       # only if n8n is in selected_services
  dbhub: dbhub                   # only if dbhub is in selected_services
  claw: claw                     # only if openclaw is in selected_services
```

Record only subdomains for services that are actually selected (foundation or optional).

During rendering, flatten these values into service placeholders:

- `subdomains.nocodb`     → `{{NOCODB_SUBDOMAIN}}`
- `subdomains.auth`       → `{{AUTHENTIK_SUBDOMAIN}}`
- `subdomains.home`       → `{{HOMEPAGE_SUBDOMAIN}}`
- `subdomains.status`     → `{{UPTIME_KUMA_SUBDOMAIN}}`
- `subdomains.dockge`     → `{{DOCKGE_SUBDOMAIN}}`
- `subdomains.n8n`        → `{{N8N_SUBDOMAIN}}`
- `subdomains.dbhub`      → `{{DBHUB_SUBDOMAIN}}`
- `subdomains.claw`       → `{{OPENCLAW_SUBDOMAIN}}`
