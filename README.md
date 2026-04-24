# FayaaSRV

**Turn any spare machine into your own private cloud — guided by an AI agent, not a shell script.**

FayaaSRV is a personal server kit. Point a coding agent (Claude Code, Codex, Copilot CLI, etc.) at this repo and it will interview you, set everything up, and hand you back a working server with real HTTPS domains, a database, automation tools, and a no-code app builder.

No memorizing flags. No copy-pasting ten commands. You answer a few questions, the agent does the rest.

---

## Why FayaaSRV

- **You own your data.** Everything runs on your hardware. No SaaS bills, no vendor lock-in.
- **Real domains, real HTTPS.** Caddy + Cloudflare Tunnel give you `nocodb.yourdomain.com` style URLs without opening a single port on your router.
- **Agent-driven setup.** Instead of a fragile install script, an AI agent reads the repo, asks what you want, and installs only what you need — explaining each step as it goes.
- **Batteries included.** PostgreSQL, NocoDB (Airtable-style no-code), n8n (workflow automation), and more — all pre-wired to talk to each other.
- **Safe by default.** No raw `sudo` loops, no hand-edited sudoers files. A scoped privileged helper does the few root tasks and nothing else.
- **Reproducible.** Your answers live in one file. Rebuild the same server on new hardware in minutes.

---

## What You Get

Always installed:
- **Caddy** — automatic HTTPS reverse proxy
- **Cloudflared** — secure tunnel to the internet, no port forwarding
- **PostgreSQL** — one shared database for all services
- **NocoDB** — no-code database / spreadsheet UI, like your own Airtable

Optional (pick what you want):
- **n8n** — visual workflow automation, like your own Zapier
- **DBHub** — expose your database to AI agents over MCP
- **OpenClaw** — bring Claude Code skills to your server

---

## Before You Start

You'll need:
1. A Linux machine (Ubuntu is the tested target) or a Mac for dev.
2. A domain name on **Cloudflare** (free plan is fine).
3. An **AI coding agent** installed on the machine — any of:
   - [Claude Code](https://claude.ai/code)
   - [GitHub Copilot CLI](https://github.com/github/gh-copilot)
   - [Codex CLI](https://github.com/openai/codex)
4. `git` installed.

That's it. You don't need Docker, Node, or Postgres ready — the agent handles those.

---

## Installation

On the machine you want to turn into your server:

**1. Clone the repo**

```bash
git clone https://github.com/FayaaDev/FayaaSRV.git
cd FayaaSRV
```

**2. Start your coding agent** from inside the `FayaaSRV` folder.

**3. Paste this prompt** into the agent:

```text
Read README.md and AGENT_PROTOCOL.md first, then use this repo as the installer:
ask the question files in order, record answers in `.fss-state.yaml`, auto-detect
host values when instructed, do not write outside the repo until Phase 6
(`questions/06-confirm.md`), use the helper-first Linux privilege flow instead of
raw sudo for normal step execution, then after confirmation execute
`steps/00-prereqs.md` through `steps/90-verify.md` in order and stop on any
failed `## Verify` block until it is fixed.
```

**4. Answer the questions.** The agent will walk you through six short topics:

1. Platform (Linux or Mac)
2. Your identity and where files should live
3. Which optional services you want
4. Your Cloudflare domain and tunnel
5. Secrets (database password, etc.)
6. Final confirmation before anything is touched

**5. Confirm, then let it run.** After Phase 6, the agent installs Docker, sets up the tunnel, provisions PostgreSQL, launches your chosen services, and wires up HTTPS routes.

**6. Done.** When the verification step passes, visit:

- `https://nocodb.yourdomain.com`
- `https://n8n.yourdomain.com` *(if selected)*
- `https://dbhub.yourdomain.com` *(if selected)*

---

## How It Works

```
Internet → Cloudflare → private tunnel → Caddy → your services
```

- **No open ports.** Cloudflare Tunnel is an outbound connection, so your home IP stays hidden and your router stays untouched.
- **One database, many apps.** A single PostgreSQL instance serves every service, keeping things simple and backup-friendly.
- **All state in one file.** Your answers live in `.fss-state.yaml`. Delete a service, tweak a subdomain, or migrate to new hardware by replaying the same state.

---

## Rebuilding or Extending

- **Change something later?** Re-run the agent with the same repo. It picks up `.fss-state.yaml` and only does what's needed.
- **Move to new hardware?** Copy the repo (with `.fss-state.yaml`) and your Docker volumes over. Re-run the agent.
- **Want more services?** The `registry.yaml` catalog and `steps/` folder are designed to be extended. Drop in a new step, the agent picks it up.

---

## For Contributors / Curious Operators

Under the hood:

- `AGENT_PROTOCOL.md` — exact rules the installer agent follows
- `questions/` — the interview, in order
- `steps/` — the install steps, each with a `## Verify` block the agent must pass
- `templates/` — config files rendered with your answers
- `registry.yaml` — service catalog and defaults
- `lib/` — shared placeholders and validation rules
- `docs/` — reference material from the live FayaaLink server
- `DRY_RUN_REPORT.md` — clean-machine validation log

The privilege model is deliberately narrow: a root-owned helper at `/usr/local/libexec/fayaasrv-root-helper` with a scoped `sudoers.d` rule. One bootstrap trust event installs it; everything after goes through the helper. No blanket `NOPASSWD`, no hand-edited sudoers.

---

## Status

v1 ships Caddy, Cloudflared, PostgreSQL, NocoDB (always), plus optional n8n, DBHub, and OpenClaw. Backups, ChangeDetection, Superset, and the broader FayaaLink service set are planned for later releases.

Validation runs are recorded in `DRY_RUN_REPORT.md`. The repo is considered public-ready only after clean-machine runs pass there.

---

## License

See repository for license details.
