# Rakkib

**Turn any spare machine into your own private cloud — guided by an AI agent, not a shell script.**

Rakkib is a personal server kit. Point a coding agent (Claude Code, Codex, Copilot CLI, etc.) at this repo and it will interview you, set everything up, and hand you back a working server with real HTTPS domains, a database, automation tools, and a no-code app builder.

No memorizing flags. No copy-pasting ten commands. You answer a few questions, the agent does the rest.

---

## Why Rakkib

- **You own your data.** Everything runs on your hardware. No SaaS bills, no vendor lock-in.
- **Real domains, real HTTPS.** Caddy + Cloudflare Tunnel give you `nocodb.yourdomain.com` style URLs without opening a single port on your router.
- **Agent-driven setup.** Instead of a fragile install script, an AI agent reads the repo, asks what you want, and installs only what you need — explaining each step as it goes.
- **Batteries included.** PostgreSQL, NocoDB (Airtable-style no-code), n8n (workflow automation), and more — all pre-wired to talk to each other.
- **Safe by default.** No raw `sudo` loops, no hand-edited sudoers files. A scoped privileged helper does the few root tasks and nothing else.
- **Reproducible.** Your answers live in one file. Rebuild the same server on new hardware in minutes.
- **Re-runnable.** A preflight doctor and idempotency rules make repeat applies safe instead of duplicating services or overwriting secrets.

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
   - [OpenCode] (https://opencode.ai)
   - [Codex CLI](https://github.com/openai/codex)
4. `git` installed.

That's it. You don't need Docker, Node, or Postgres ready — the agent handles those.

---

## Installation

On the machine you want to turn into your server:

**Fast bootstrap option**

```bash
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash
```

The bootstrapper clones or updates this repo, runs `scripts/rakkib-doctor`, then launches a supported agent CLI. If multiple supported agents are installed, it asks which one to use; if only one is installed, it launches that one. The agent still performs the actual interview, rendering, privileged helper flow, and deployment steps.

You can override the checkout path if needed:

```bash
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | RAKKIB_DIR=$HOME/Rakkib bash
```

If you want the old manual-prompt behavior instead of auto-launching an agent:

```bash
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash -s -- --print-prompt
```

To force a specific agent:

```bash
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash -s -- --agent opencode
```

**Manual clone option**

**1. Clone the repo**

```bash
git clone https://github.com/FayaaDev/Rakkib.git
cd Rakkib
```

**2. Start your coding agent** from inside the `Rakkib` folder.

**3. Paste this prompt** into the agent:

```text
Read README.md and AGENT_PROTOCOL.md first, then use this repo as the installer:
ask the question files in order, record answers in `.fss-state.yaml`, auto-detect
host values when instructed, do not write outside the repo until Phase 6
(`questions/06-confirm.md`), use the helper-first Linux privilege flow instead of
raw sudo for normal step execution, then after confirmation execute
`steps/00-prereqs.md` through `steps/90-verify.md` in numeric order, skipping
optional restore-test work unless requested, and stop on any failed `## Verify`
block until it is fixed.
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

- **Change something later?** Re-run the agent with the same repo. It picks up `.fss-state.yaml`, runs `scripts/rakkib-doctor`, and only does what's needed.
- **Move to new hardware?** Copy the repo (with `.fss-state.yaml`) and restore from a local backup archive, then re-run the agent.
- **Want more services?** The `registry.yaml` catalog and `steps/` folder are designed to be extended. Drop in a new step, the agent picks it up.

---

## License

See repository for license details.
