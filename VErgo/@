# VErgo → Rakkib Integration Difficulty Assessment

## Context

`VErgo/` was added as a sibling tree inside the Rakkib repo but is **not wired into the agent installer flow**. It is currently a standalone `curl | bash` toolkit. The user wants an assessment of how hard it would be to integrate VErgo as a first-class Rakkib component — not an implementation, just a difficulty read.

## What VErgo actually is

A **terminal/desktop dotfiles bootstrap** for macOS and Ubuntu. Two installers:

- `VErgo/terminal.sh` — zsh + Zi + Powerlevel10k + WezTerm + Meslo Nerd Fonts; deploys `~/.zshrc`, `~/.zshenv`, `~/.p10k.zsh`, `~/.wezterm.lua`. Cross-platform (mac/ubuntu).
- `VErgo/aerospace.sh` — macOS-only tiling WM stack: Aerospace + SketchyBar + JankyBorders + Tokyonight theme. Registers Aerospace as a login item via `osascript`.

All writes are user-scoped (`$HOME` only), with `~/.backup-power10k/<ts>/` backups. Per-platform templates already mirror Rakkib's `mac` vs `ubuntu` split. Internally still branded `power10k` (env vars `POWER10K_*`, raw URL `FayaaDev/power10k`); the directory rename to `VErgo` is cosmetic and references are stale.

It also ships `VErgo/opencode/command/power10k.md` — an OpenCode slash-command wrapper.

## What Rakkib is (relevant constraints)

- Agent-driven server installer: `questions/01-06` → `.fss-state.yaml` → `steps/00-90` → host. Markdown is the only "framework"; the agent does all rendering and execution.
- Has exactly **one** existing host-service precedent: OpenClaw (`registry.yaml:142-152`, `steps/70-host-agents.md`, `templates/systemd/claw-gateway.service.tmpl`, `templates/launchd/claw-gateway.plist.tmpl`, `templates/caddy/routes/claw.caddy.tmpl`).
- **No existing handling for shell/dotfile/terminal customization.** Steps never touch `~/.zshrc`, `~/.bashrc`, etc. The closest home-dir writes today are `~/.local/bin/{cloudflared,openclaw}` and the agent-memory blocks in `~/.claude/CLAUDE.md`.
- Idempotency contract (`lib/idempotency.md`) covers `.env`, compose files, Caddy, systemd/launchd — **no row for "user dotfile."**
- v1 scope (`CLAUDE.md:108-110`) explicitly excludes OpenCode host service; v1.1 plan (`v1.1-tool-expansion.md`) does not list VErgo or any terminal/dotfile component.

## Difficulty rating: **Medium-Low technically, Medium conceptually**

The mechanical work is small — Rakkib is documentation-driven, and VErgo's per-platform templates already match Rakkib's conventions. The conceptual lift is the bigger cost: VErgo introduces two patterns Rakkib has never expressed.

### Why it's mechanically easy (~1 day of work)

- Per-platform split (`*.mac.*` / `*.ubuntu.*`) already matches Rakkib's `templates/systemd/` vs `templates/launchd/` convention.
- VErgo writes only to `$HOME` — fits Rakkib's user-scoped privilege model.
- Backup-and-overwrite (`~/.backup-power10k/<ts>/`) is already idempotent in spirit.
- The OpenClaw eight-surface pattern is a clear blueprint to copy.
- Few placeholders likely needed (`{{ADMIN_USER}}`, `{{TZ}}` at most — VErgo configs are largely static).

### Why it's conceptually non-trivial

1. **New service archetype: "no-network host service."** OpenClaw is `host_service: true` but still has a port + Caddy route. A pure-dotfile component has `default_port: null`, `default_subdomain: null`, and no Caddy route. This is an untested branch in `steps/60-services.md` and `steps/70-host-agents.md`.
2. **New idempotency rule needed.** `lib/idempotency.md` has no entry for shell rc files. Decision required: preserve-user-edits (like `.env`) or full re-render (like systemd units)? Different files in VErgo want different answers — `.zshrc` is user-edited often; `.p10k.zsh` is generated and stable.
3. **Aerospace's login-item registration** uses `osascript` to mutate System Events — Rakkib has no precedent for AppleScript or login-item management. Needs a new idempotency entry.
4. **Homebrew taps** (`nikitabobko/tap`, `FelixKratz/formulae`) and **font casks** are new dependency surfaces; `steps/00-prereqs.md` only handles Docker Desktop and `cloudflared` today.
5. **OpenCode integration is v1-out-of-scope** per `CLAUDE.md:110`. Pulling `VErgo/opencode/command/` in wholesale would violate the scope statement and require a v-scope decision first.
6. **macOS Accessibility prompt** for Aerospace cannot be automated — adds a "manual user step" to Rakkib's flow, which today aims for unattended execution after confirmation.
7. **Stale `power10k` branding** inside the VErgo tree (env vars, raw URLs in `terminal.sh` and `opencode/command/power10k.md`) needs reconciliation before integration.

## Touchpoints if integration proceeds

Modeled on the OpenClaw eight-surface pattern:

| # | File | Change |
|---|---|---|
| 1 | `registry.yaml` | New entry `id: vergo`, `host_service: true`, `image: null`, `default_port: null`, `default_subdomain: null`, `depends_on: []` |
| 2 | `lib/placeholders.md` | Register any new `{{VERGO_*}}` placeholders |
| 3 | `lib/idempotency.md` | New row: "user dotfile" with backup-and-overwrite semantics |
| 4 | `questions/03-services.md` | Menu entry; **no subdomain block** (new branch) |
| 5 | `steps/00-prereqs.md` | Note Homebrew taps + font casks needed on Mac; zsh/git/curl/eza/zoxide/fzf on Ubuntu |
| 6 | `steps/70-host-agents.md` | New "VErgo" subsection: prereqs, fonts, dotfile copy with backup, optional Aerospace stack on Mac |
| 7 | `templates/vergo/` (new dir) | Move `VErgo/files/` and `VErgo/templates/` contents here, with `{{PLACEHOLDER}}` substitutions where useful |
| 8 | `steps/90-verify.md` | Verify lines: `test -f ~/.zshrc`, `grep -q powerlevel10k ~/.zshrc`, fonts present |
| 9 | `templates/agent-memory/SERVER_README.md.tmpl` | Add VErgo summary line |
| 10 | `CLAUDE.md` v1-scope block | Declare v-scope: v1.1 add-on, or v2-only |

## Open design questions for the user

1. **Scope** — is VErgo intended for v1, v1.1, or v2? Currently undeclared.
2. **OpenCode** — keep `VErgo/opencode/` excluded (per current `CLAUDE.md:110`), or revisit the OpenCode-in-v1 scope decision?
3. **Aerospace** — bundle with VErgo, gate behind a separate question, or leave out as a manual `aerospace.sh` post-install?
4. **Idempotency policy for dotfiles** — preserve user edits (merge-only) or full re-render with backup? My read: full re-render with backup, since VErgo already does this and dotfile drift is the whole point of running it again.
5. **Branding** — rename `power10k` references inside `VErgo/` to `vergo`, or keep `power10k` as the upstream identity and treat VErgo as the embedded copy?

## Verification (how you'd test integration end-to-end, when ready)

- Run the canonical operator prompt against a fresh Mac VM and a fresh Ubuntu VM.
- After Phase 6, confirm `selected_services` includes `vergo` (when chosen).
- After step 70: `test -f ~/.zshrc && grep -q powerlevel10k ~/.zshrc`, `fc-list | grep -i meslo`, `test -f ~/.wezterm.lua`. On Mac with Aerospace selected: `test -f ~/.config/aerospace/aerospace.toml`, login-item registered (`osascript -e 'tell application "System Events" to get the name of every login item'`).
- Step 90 verify must pass without manual fixes.
- Re-run the install — confirm dotfiles re-render cleanly without duplicating backups or breaking shells.

## Bottom line

If you want a number: **~1 day of focused work** to wire VErgo in mechanically, plus **a 30-minute design call** to settle the five open questions above. The blockers are policy (scope, idempotency rule, Aerospace bundling), not code.
