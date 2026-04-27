# Rakkib

Rakkib is an agent-driven personal server kit. A coding agent interviews you, records answers in `.fss-state.yaml`, renders templates, and executes verified setup steps to bring up your selected services.

## Quickstart

```bash
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/Simplify/install.sh | bash
rakkib init
```

For a local clone:

```bash
git clone https://github.com/FayaaDev/Rakkib.git
cd Rakkib
bash install.sh
rakkib init
```

## How It Works

- `install.sh` clones or updates this repo, creates a project-local venv at `<repo>/.venv`, installs the rakkib package into it, and symlinks `~/.local/bin/rakkib` to the venv's entry-point script.
- `rakkib init` runs diagnostics and launches a supported agent with the canonical installer prompt.
- `AGENT_PROTOCOL.md` is the normative installer spec. It defines the interview, state, rendering, privilege, execution, and verification rules.
- `registry.yaml` is the canonical service catalog.
- `steps/` contains the execution gates. Each step must pass its own `## Verify` block before the agent advances.

## Useful Commands

```bash
rakkib init                # start or resume the agent-led setup
rakkib init --print-prompt # print the prompt instead of launching an agent
rakkib init --agent codex  # force a supported agent CLI
rakkib doctor              # run host diagnostics
rakkib auth sudo           # validate sudo for the current terminal
rakkib prompt              # print the canonical installer prompt
```

Root-only helper actions are allowlisted:

```bash
sudo rakkib privileged check
sudo rakkib privileged ensure-layout --state .fss-state.yaml
sudo rakkib privileged fix-repo-owner --state .fss-state.yaml
```

## Requirements

- Ubuntu Linux is the tested deployment target. macOS is supported for development and host customization paths.
- Use a normal sudo-capable admin user. Do not run the full agent session as root by default.
- Use a domain on Cloudflare for public HTTPS routes.
- Install at least one supported coding agent CLI: OpenCode, Claude Code, or Codex.

## License

See repository for license details.
