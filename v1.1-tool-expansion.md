# Rakkib v1.1 — Tool Expansion Plan

## Context

Rakkib v1 ships a foundational stack: Caddy + Cloudflared + Postgres
(pgvector) + NocoDB, with optional n8n, DBHub, and OpenClaw. The product
positioning is "Ninite for home servers" — a guided installer that gives
a fresh Linux box a working set of the tools self-hosters actually run.

To grow into that positioning, v1.1 expands the catalog with the
most-installed self-hosted apps. Selections are organized first by
**criticality** (must-haves on par with Docker itself) and then by
**utility category**, so the interview phase can offer a sensible bundle
rather than a flat list of 15 checkboxes.

This document is a planning artifact. It does not modify any code.

---

## Tier 0 — Foundation (must-haves, "as important as Docker")

These are infrastructure services that **every other service benefits
from**. Once a server hosts more than a handful of apps, going without
them is painful enough that they belong alongside Caddy / Cloudflared /
Postgres in the foundational tier — not in the optional pool.

| Service          | Role               | Why it's foundational                                                                                                                       |
| ---------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Authentik**    | SSO / auth proxy   | Single login for NocoDB / n8n / DBHub / Vaultwarden / etc. Without it, every new service is a new auth surface. Postgres-backed.            |
| **Homepage**     | Service dashboard  | The "front door" — auto-discovers Docker services and becomes the home page of the server. UX glue for the whole installer.                 |
| **Uptime Kuma**  | Monitoring         | Watches every Caddy route. Without it, outages are discovered by the user trying to use a thing.                                            |
| **Dockge**       | Compose UI         | Manages the very compose stacks Rakkib generates. Lets users tweak / restart services without SSH.                                          |

Promotion rationale: each of these is a *force multiplier* on the rest of
the catalog. Authentik makes every other service safer to expose.
Homepage makes them discoverable. Uptime Kuma makes them observable.
Dockge makes them maintainable. Skipping any of the four leaves a real
gap that the user has to solve manually before the server is usable.

---

## Tier 1 — High utility, by category

Optional but very widely deployed. Grouped by the user need they serve so
the interview can present checkbox bundles instead of a flat list.

### Security & Identity

| Service         | Notes                                                                                                                |
| --------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Vaultwarden** | Self-hosted Bitwarden-compatible password manager. Postgres-backed. One of the most-installed homelab apps.          |
| **AdGuard Home**| DNS-level ad and tracker blocking. Complements Cloudflared without conflict (Cloudflared handles inbound, AdGuard handles outbound DNS). |

### Backup, Sync & Network

| Service       | Notes                                                                                                                                  |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Syncthing** | Peer-to-peer file sync. No DB, no auth dependency, runs anywhere.                                                                      |
| **Tailscale** | Mesh VPN for non-public services. Complements Cloudflared (which fronts the public ones). Host service, not a container.               |

### Media & Photos

| Service      | Notes                                                                                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Immich**   | Google Photos replacement. **Pgvector synergy** — uses the existing pgvector database for ML face / object search. Unique selling point of this stack.             |
| **Jellyfin** | Plex-style media server. No DB dependency. Most-installed media app in the self-hosted scene.                                                                      |

### Files & Documents

| Service         | Notes                                                                                                  |
| --------------- | ------------------------------------------------------------------------------------------------------ |
| **Nextcloud**   | Dropbox / Google Drive replacement. Postgres-backed.                                                   |
| **Paperless-ngx** | Document scanning, OCR, full-text search. Postgres-backed.                                           |

### Smart Home

| Service           | Notes                                                                                                            |
| ----------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Home Assistant**| The defining "home server" application for many users. Runs as its own container, no postgres dependency.        |

### AI / LLM

| Service        | Notes                                                                                                |
| -------------- | ---------------------------------------------------------------------------------------------------- |
| **Ollama**     | Local LLM runtime. Pairs with the existing OpenClaw / n8n AI direction.                              |
| **Open WebUI** | ChatGPT-style UI in front of Ollama. Postgres-backed.                                                |

### Developer / Code

| Service     | Notes                                                                          |
| ----------- | ------------------------------------------------------------------------------ |
| **Forgejo** | Self-hosted Git forge (Gitea fork). Postgres-backed. Pairs with n8n CI flows.  |

### Productivity & Notes

| Service    | Notes                                                                          |
| ---------- | ------------------------------------------------------------------------------ |
| **Memos**  | Quick-note / microblog server. Postgres-backed. Lightweight alternative to a wiki. |

---

## Architectural Notes

- **Pgvector synergy.** Immich's ML search uses pgvector. The interview
  should highlight this — most installers can't say "your photo search
  is already optimized for AI from the moment you turn it on."
- **Authentik first.** If the user opts into Authentik, downstream
  services should be configured to federate with it from the start
  (OAuth or proxy-outpost), rather than retrofitting auth later.
- **Caddy auto-routing.** Every new service follows the existing
  `<svc>.<domain>` subdomain pattern via the Caddy + Cloudflared chain.
- **Postgres reuse.** Every postgres-backed service gets a database and
  user provisioned in the existing single postgres instance — same model
  as n8n and NocoDB today.
- **Host services.** Only OpenClaw (existing) and Tailscale (new) install
  on the host. Everything else is a container under `caddy_default`.

---

## Files to modify

1. **`registry.yaml`** — add an entry per new service with `image`,
   `default_port`, `default_subdomain`, `env_keys`, `depends_on`,
   `host_service`, and `notes`. Tier 0 services are added with
   `required: true` once the user opts into the v1.1 foundation tier;
   the rest are `optional: true`.
2. **`lib/placeholders.md`** — register every new `{{PLACEHOLDER}}`
   (DB passwords, admin emails, Authentik `AUTHENTIK_SECRET_KEY`, Immich
   JWT secret, Vaultwarden admin token, etc.).
3. **`questions/`** — extend the service-selection question (currently
   in `questions/03-*` based on the directory layout) to present the
   categorized bundles above, plus update `questions/06-confirm.md` so
   the confirmation summary covers the new selections.
4. **`templates/services/<svc>/`** — one compose template per new
   service, plus any config files (Authentik blueprints, Homepage
   `services.yaml`, Uptime Kuma seed, Immich `.env`, etc.).
5. **`steps/`** — add or extend step files so each new service has its
   own `## Inputs` / `## Actions` / `## Verify` block. Per-service
   verify must cover:
   - Postgres database and user provisioned (where applicable).
   - Compose `up` succeeds and the container is healthy.
   - Caddy route resolves locally.
   - Cloudflared subdomain reachable from outside (if
     `cloudflare.zone_in_cloudflare` is true).
   - Service-specific health endpoint returns OK.
6. **`steps/90-verify.md`** — extend final post-install verification to
   cover the new services.
7. **`templates/agent-memory/SERVER_README.md.tmpl`** and
   **`templates/agent-memory/CLAUDE.md.tmpl`** — update so the
   post-install agent memory documents the new services and their URLs
   inside the `<!-- RAKKIB START --> / <!-- RAKKIB END -->` block.

---

## Rollout strategy

Land in waves so each wave is a self-contained, reviewable change:

1. **Wave A — Tier 0 foundation.** Authentik → Homepage → Uptime Kuma →
   Dockge. Architectural; best done together because Homepage references
   the others, Authentik fronts the others, and Uptime Kuma probes the
   others.
2. **Wave B — Security & Identity.** Vaultwarden, AdGuard Home.
3. **Wave C — Media & Photos.** Immich (showcase the pgvector wiring),
   Jellyfin.
4. **Wave D — Files & Documents.** Nextcloud, Paperless-ngx.
5. **Wave E — Smart Home & AI.** Home Assistant, Ollama, Open WebUI.
6. **Wave F — Developer & Productivity.** Forgejo, Memos.
7. **Wave G — Network.** Syncthing, Tailscale (host service).

Each wave is one PR: registry + placeholders + step + template + verify
in a single change.

---

## Verification (end-to-end, all v1.1 services selected)

1. `docker ps` — every new container is on the `caddy_default` network
   and reports healthy.
2. `curl -I https://<svc>.<domain>/` returns 200 / 302 for every new
   subdomain (`authentik`, `home`, `status`, `dockge`, `vault`,
   `photos`, `media`, `cloud`, `paperless`, `ha`, `ollama`, `chat`,
   `git`, `notes`, `dns`).
3. Authentik admin UI lists each Tier 1 service as a registered
   application (OAuth or proxy outpost).
4. Homepage auto-discovers and renders every other service tile.
5. Uptime Kuma probes every Caddy route as green.
6. Immich: upload a sample photo and confirm ML search returns
   ML-ranked results — confirms pgvector is wired through.
7. `psql -U postgres -l` shows separate databases for each
   postgres-backed service.
8. `~/.claude/CLAUDE.md` and any `~/.config/github-copilot/AGENTS.md` /
   `~/.codex/AGENTS.md` files reflect the new services inside the
   `<!-- RAKKIB START -->` block.
9. From a Tailscale-connected device (if selected), non-public services
   are reachable on their internal addresses without going through
   Cloudflared.
