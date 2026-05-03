# Question File 03 — Services

**Phase 3 of 6. No writes outside the repo occur during this phase.**

## AgentSchema

```yaml
schema_version: 1
phase: 3
reads_state:
  - domain
writes_state:
  - foundation_services
  - selected_services
  - host_addons
  - subdomains
service_catalog:
  foundation_bundle:
    - slug: nocodb
      label: NocoDB
      numeric_alias: 1
      subdomain_key: nocodb
      default_subdomain: nocodb
    - slug: homepage
      label: Homepage
      numeric_alias: 2
      subdomain_key: homepage
      default_subdomain: home
    - slug: uptime-kuma
      label: Uptime Kuma
      numeric_alias: 3
      subdomain_key: uptime-kuma
      default_subdomain: status
    - slug: dockge
      label: Dockge
      numeric_alias: 4
      subdomain_key: dockge
      default_subdomain: dockge
  optional_services:
    - slug: n8n
      label: n8n
      numeric_alias: 6
      subdomain_key: n8n
      default_subdomain: n8n
    - slug: immich
      label: Immich
      numeric_alias: 7
      subdomain_key: immich
      default_subdomain: immich
    - slug: transfer
      label: transfer.sh
      numeric_alias: 8
      subdomain_key: transfer
      default_subdomain: transfer
    - slug: jellyfin
      label: Jellyfin
      numeric_alias: 9
      subdomain_key: jellyfin
      default_subdomain: jellyfin
    - slug: openclaw
      label: OpenClaw
      numeric_alias: 10
      subdomain_key: openclaw
      default_subdomain: claw
    - slug: filebrowser
      label: File Browser
      numeric_alias: 12
      subdomain_key: filebrowser
      default_subdomain: files
    - slug: it-tools
      label: IT-Tools
      numeric_alias: 13
      subdomain_key: it-tools
      default_subdomain: tools
    - slug: cyberchef
      label: CyberChef
      numeric_alias: 14
      subdomain_key: cyberchef
      default_subdomain: cyberchef
    - slug: drawio
      label: Draw.io
      numeric_alias: 15
      subdomain_key: drawio
      default_subdomain: drawio
    - slug: excalidraw
      label: Excalidraw
      numeric_alias: 16
      subdomain_key: excalidraw
      default_subdomain: excalidraw
  host_addons:
    - slug: vergo_terminal
      label: VErgo Terminal
      numeric_alias: 11
fields:
  - id: foundation_services
    type: multi_select
    selection_mode: deselect_from_default
    prompt: "Foundation Bundle: type service slugs to deselect (e.g. `homepage dockge`); numeric aliases like `2 4` are also accepted, or press Enter to accept all:"
    canonical_values: [nocodb, homepage, uptime-kuma, dockge]
    numeric_aliases:
      "1": nocodb
      "2": homepage
      "3": uptime-kuma
      "4": dockge
    records:
      - foundation_services
  - id: optional_services
    type: multi_select
    selection_mode: add_to_empty
    prompt: "Service categories: type service slugs to add (e.g. `n8n immich filebrowser`); numeric aliases like `6 8 12` are also accepted, or press Enter to skip all:"
    canonical_values: [n8n, immich, transfer, jellyfin, openclaw, filebrowser, it-tools, cyberchef, drawio, excalidraw]
    numeric_aliases:
      "6": n8n
      "7": immich
      "8": transfer
      "9": jellyfin
      "10": openclaw
      "12": filebrowser
      "13": it-tools
      "14": cyberchef
      "15": drawio
      "16": excalidraw
    records:
      - selected_services
  - id: host_addons
    type: multi_select
    selection_mode: add_to_empty
    prompt: "Host Addons: type addon slugs to add (e.g. `vergo_terminal`); numeric aliases like `11` are also accepted, or press Enter to skip all:"
    canonical_values: [vergo_terminal]
    numeric_aliases:
      "11": vergo_terminal
    records:
      - host_addons
  - id: service_subdomain
    type: text
    repeat_for: selected_service_slugs
    prompt_template: "Subdomain for <service>? [default: <default>]"
    records:
      - subdomains
rules:
  - if_selected: transfer
    require_confirm: transfer_public_risk
```

---

## Instructions for the Agent

Present the full service menu below as a TUI-style checklist. Collect selections in three rounds:
1. **Foundation Bundle** — all pre-selected; user types service slugs to deselect.
2. **Service categories** — none pre-selected; user types service slugs to select.
3. **Host Addons** — none pre-selected; user types addon slugs to select.

Numeric checklist positions may still be accepted as convenience aliases, but canonical recorded inputs are always slugs.

When rendering the checklist, the selectable label must always be the service or addon name shown below (`NocoDB`, `Homepage`, `VErgo Terminal`, etc.). Use `[✓]` and `[ ]` only as visual state markers. Do not render `selected`, `unselected`, `true`, or `false` as an option label.

Subdomains are automatically set to the defaults from the service catalog. Record all results into `.fss-state.yaml`. Do not advance to `questions/04-cloudflare.md` until recording is complete.

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
  [✓] 2  Homepage      — service dashboard      →  home.<domain>
  [✓] 3  Uptime Kuma   — uptime monitoring      →  status.<domain>
  [✓] 4  Dockge        — Compose manager        →  dockge.<domain>

Automation:
  [ ] 6  n8n           — workflow automation    →  n8n.<domain>

Media:
  [ ] 7  Immich        — photo library          →  immich.<domain>
  [ ] 9  Jellyfin      — media server           →  jellyfin.<domain>

File Sharing:
  [ ] 8  transfer.sh   — public file sharing    →  transfer.<domain>
  [ ] 12 File Browser  — browser file manager   →  files.<domain>

AI:
  [ ] 10 OpenClaw      — AI assistant gateway   →  claw.<domain>

Developer Tools:
  [ ] 13 IT-Tools      — browser utilities      →  tools.<domain>
  [ ] 14 CyberChef     — data transformation    →  cyberchef.<domain>

Diagram And Design:
  [ ] 15 Draw.io       — diagramming app        →  drawio.<domain>
  [ ] 16 Excalidraw    — sketch whiteboard      →  excalidraw.<domain>

Host Addons:
  [ ] 11 VErgo Terminal — zsh, prompt, completions, CLI UX
```

---

## Round 1 — Foundation Bundle

Ask:

> "Foundation Bundle: type service slugs to deselect (e.g. `homepage dockge`); numeric aliases like `2 4` are also accepted, or press Enter to accept all:"

- Parse the response as a space-separated list of canonical service slugs.
- Accept the numeric aliases shown in the checklist as a convenience input and normalize them to the same canonical service slugs before recording state.
- Remove the corresponding services from the selected foundation set.
- If the user presses Enter with no input, keep all four selected.
- Re-render the updated checklist showing `[✓]` / `[ ]` states and ask the user to confirm.

---

## Round 2 — Service Categories

Ask:

> "Service categories: type service slugs to add (e.g. `n8n immich filebrowser`); numeric aliases like `6 8 12` are also accepted, or press Enter to skip all:"

- Parse the response as a space-separated list of canonical service slugs.
- Accept the numeric aliases shown in the checklist as a convenience input and normalize them to the same canonical service slugs before recording state.
- Add the corresponding services to the selection.
- If the user presses Enter with no input, none are selected.
- If `8` selects `transfer`, warn before recording it: "transfer.sh will be deployed as a public unauthenticated upload endpoint. Anyone who can reach the URL can upload files. Rakkib does not put transfer.sh behind HTTP basic auth because that interferes with its CLI/API behavior." Ask the user to confirm they accept this risk before recording `transfer`; do not record it if they decline.

---

## Round 3 — Host Addons

Ask:

> "Host Addons: type addon slugs to add (e.g. `vergo_terminal`); numeric aliases like `11` are also accepted, or press Enter to skip all:"

- Parse the response as a space-separated list of canonical addon slugs.
- Accept the numeric aliases shown in the checklist as a convenience input and normalize them to the same canonical addon slugs before recording state.
- `11` selects `vergo_terminal`.
- If the user presses Enter with no input, no host addons are selected.
- Warn before recording `vergo_terminal`: "VErgo Terminal modifies the admin user's shell dotfiles (`~/.zshrc`, `~/.zshenv`, `~/.p10k.zsh`, and on Mac `~/.wezterm.lua`). Existing files are backed up before replacement."

---

## Record in .fss-state.yaml

```yaml
foundation_services:
  - nocodb
  - homepage
  - uptime-kuma
  - dockge
selected_services:
  - n8n
host_addons:
  - vergo_terminal
subdomains:
  nocodb: nocodb
  homepage: home
  uptime-kuma: status
  dockge: dockge
  n8n: n8n
  immich: immich
  transfer: transfer
  jellyfin: jellyfin
  openclaw: claw
  filebrowser: files
  it-tools: tools
  cyberchef: cyberchef
  drawio: drawio
  excalidraw: excalidraw
```

Record only subdomains for services that are actually selected (foundation or optional).
Do not introduce alias subdomain keys in new state files. Use the service slug as the only `subdomains.*` key.

During rendering, flatten these values into service placeholders:

- `subdomains.nocodb` -> `{{NOCODB_SUBDOMAIN}}`
- `subdomains.homepage` -> `{{HOMEPAGE_SUBDOMAIN}}`
- `subdomains.uptime-kuma` -> `{{UPTIME_KUMA_SUBDOMAIN}}`
- `subdomains.dockge` -> `{{DOCKGE_SUBDOMAIN}}`
- `subdomains.n8n` -> `{{N8N_SUBDOMAIN}}`
- `subdomains.immich` -> `{{IMMICH_SUBDOMAIN}}`
- `subdomains.transfer` -> `{{TRANSFER_SUBDOMAIN}}`
- `subdomains.jellyfin` -> `{{JELLYFIN_SUBDOMAIN}}`
- `subdomains.openclaw` -> `{{OPENCLAW_SUBDOMAIN}}`
- `subdomains.filebrowser` -> `{{FILEBROWSER_SUBDOMAIN}}`
- `subdomains.it-tools` -> `{{IT_TOOLS_SUBDOMAIN}}`
- `subdomains.cyberchef` -> `{{CYBERCHEF_SUBDOMAIN}}`
- `subdomains.drawio` -> `{{DRAWIO_SUBDOMAIN}}`
- `subdomains.excalidraw` -> `{{EXCALIDRAW_SUBDOMAIN}}`
