"""Rakkib CLI entrypoint.

Commands: init, doctor, status, add, uninstall, privileged, auth
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from rakkib.agent_handoff import handoff
from rakkib.doctor import (
    attempt_fix_cloudflared,
    attempt_fix_docker,
    process_owners_for_ports,
    run_checks,
    summary_text,
    to_json,
)
from rakkib.interview import run_interview
from rakkib.state import State
from rakkib.steps import VerificationResult
from rakkib.steps import services as services_step

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_root(ctx: click.Context) -> None:
    if os.geteuid() != 0:
        console.print("[bold red]Error:[/bold red] This helper must be run with sudo or from a root shell.")
        ctx.exit(1)


def _resolve_admin_user(state: State, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    user = state.get("admin_user")
    if user:
        return str(user)
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user and sudo_user != "root":
        return sudo_user
    console.print("[red]Admin user is required; pass --admin-user or record admin_user in state.[/red]")
    raise click.Abort()


def _update_readme_agent_memory(repo_dir: Path, state: State) -> None:
    """Append or update the Agent Memory block in README.md."""
    readme_path = repo_dir / "README.md"
    if not readme_path.exists():
        return

    foundation = state.get("foundation_services") or []
    selected = state.get("selected_services") or []
    data_root = state.get("data_root", "/srv")
    domain = state.get("domain", "") or ""

    foundation_str = ", ".join(foundation) if foundation else "None"
    selected_str = ", ".join(selected) if selected else "None"

    block = (
        "<!-- BEGIN RAKKIB AGENT MEMORY -->\n"
        "## Deployed Services\n"
        "\n"
        f"- **Foundation**: {foundation_str}\n"
        f"- **Optional**: {selected_str}\n"
        f"- **Data Root**: {data_root}\n"
        f"- **Domain**: {domain}\n"
        "\n"
        "<!-- END RAKKIB AGENT MEMORY -->\n"
    )

    content = readme_path.read_text()
    start_marker = "<!-- BEGIN RAKKIB AGENT MEMORY -->"
    end_marker = "<!-- END RAKKIB AGENT MEMORY -->"

    if start_marker in content and end_marker in content:
        start_idx = content.index(start_marker)
        end_idx = content.index(end_marker) + len(end_marker)
        # Strip trailing whitespace/newlines from the remainder so we don't accumulate blanks
        after = content[end_idx:]
        content = content[:start_idx] + block + after
    else:
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + block

    readme_path.write_text(content)


def _check_docker() -> bool:
    """Verify docker and docker compose are available. Offer to install if missing."""
    if shutil.which("docker") is None:
        console.print("[bold red]Docker is required but not found on PATH.[/bold red]")
        console.print(
            "Install Docker: https://docs.docker.com/engine/install/ubuntu/#installation-methods"
        )
        from rakkib.tui import prompt_confirm
        if prompt_confirm("Install Docker now? (uses get.docker.com convenience script)", default=True):
            from rakkib.doctor import attempt_fix_docker
            result = attempt_fix_docker()
            console.print(f"[dim]{result}[/dim]")
            if shutil.which("docker") is None:
                console.print("[bold red]Docker installation did not succeed. Aborting.[/bold red]")
                return False
            console.print("[green]Docker installed successfully.[/green]")
        else:
            return False

    compose_check = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True,
    )
    if compose_check.returncode != 0:
        console.print("[bold red]docker compose (v2 plugin) is required but not available.[/bold red]")
        console.print("Install the Docker Compose plugin: https://docs.docker.com/compose/install/")
        return False

    return True


def _run_steps(
    state: State,
    repo_dir: Path,
    agent: str = "auto",
    print_prompt: bool = False,
    no_agent: bool = False,
) -> bool:
    """Execute setup steps in order. Return True if all pass."""
    if not _check_docker():
        return False

    steps: list[tuple[str, str]] = [
        ("10", "rakkib.steps.layout"),
        ("30", "rakkib.steps.caddy"),
        ("40", "rakkib.steps.cloudflare"),
        ("50", "rakkib.steps.postgres"),
        ("60", "rakkib.steps.services"),
        ("80", "rakkib.steps.cron"),
        ("90", "rakkib.steps.verify"),
    ]

    for label, module_path in steps:
        console.print(f"[bold green]Step {label}[/bold green]")
        try:
            module = __import__(module_path, fromlist=["run", "verify"])
            run_fn = getattr(module, "run", None)
            verify_fn = getattr(module, "verify", None)

            if run_fn is None:
                console.print(f"[yellow]  Step {label} module has no run() — skipping[/yellow]")
                continue

            run_fn(state)

            if verify_fn is not None:
                result = verify_fn(state)
                if not result.ok:
                    console.print(f"[bold red]  Step {label} verify failed:[/bold red] {result.message}")
                    if result.log_path:
                        console.print(f"[dim]  Log: {result.log_path}[/dim]")

                    handoff(
                        step=result.step,
                        message=result.message,
                        log_path=result.log_path,
                        state=state,
                        repo_dir=repo_dir,
                        agent=agent,
                        print_prompt=print_prompt,
                        no_agent=no_agent,
                    )
                    return False
                console.print(f"[dim]  Step {label} verify passed[/dim]")
            else:
                console.print(f"[dim]  Step {label} has no verify() — skipping check[/dim]")

        except Exception as exc:
            console.print(f"[bold red]  Step {label} failed:[/bold red] {exc}")

            handoff(
                step=module_path.rsplit(".", 1)[-1],
                message=f"{type(exc).__name__}: {exc}",
                log_path=None,
                state=state,
                repo_dir=repo_dir,
                agent=agent,
                print_prompt=print_prompt,
                no_agent=no_agent,
            )
            return False

    console.print("[bold green]All steps completed successfully.[/bold green]")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version=__import__("rakkib").__version__, prog_name="rakkib")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Rakkib — agent-driven personal server kit."""
    ctx.ensure_object(dict)
    if "repo_dir" not in ctx.obj:
        ctx.obj["repo_dir"] = Path(__file__).resolve().parent


@cli.command()
@click.option("--agent", type=str, default="auto", help="Agent mode: auto, opencode, claude, codex, none")
@click.option("--print-prompt", is_flag=True, help="Print the agent prompt and exit")
@click.option("--no-agent", is_flag=True, help="Equivalent to --agent none")
@click.option("--resume", is_flag=True, help="Skip interview and run steps directly if state is confirmed")
@click.pass_context
def init(ctx: click.Context, agent: str, print_prompt: bool, no_agent: bool, resume: bool) -> None:
    """Run diagnostics and launch the setup wizard."""
    if no_agent:
        agent = "none"

    console.print("[bold green]Rakkib init[/bold green]")

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    # --resume explicitly skips the interview and runs steps directly
    if resume:
        if not state.is_confirmed():
            console.print("[yellow]State is not confirmed — cannot resume. Run `rakkib init` without --resume to complete the interview.[/yellow]")
            return
        console.print("[dim]--resume set — skipping interview, resuming step execution.[/dim]")
        _run_steps(state, repo_dir, agent=agent, print_prompt=print_prompt, no_agent=no_agent)
        return

    # Always go through run_interview — it handles the confirmed-state case
    # by asking "Start over?" before proceeding
    state = run_interview(state, questions_dir=repo_dir / "data" / "questions")
    state.save(state_path)
    console.print("[bold green]Interview complete. State saved to .fss-state.yaml[/bold green]")

    if state.is_confirmed():
        _run_steps(state, repo_dir, agent=agent, print_prompt=print_prompt, no_agent=no_agent)
    else:
        console.print("[yellow]State is not confirmed — run `rakkib init` again to confirm and execute steps.[/yellow]")


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output")
@click.option("--interactive", is_flag=True, help="Interactive mode with auto-fix prompts")
@click.pass_context
def doctor(ctx: click.Context, json_output: bool, interactive: bool) -> None:
    """Run host diagnostics."""
    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    checks = run_checks(state)

    if json_output:
        click.echo(to_json(checks))
    else:
        if interactive:
            from rich.panel import Panel
            from rich.table import Table

            table = Table(title="Rakkib Doctor", show_header=True, header_style="bold magenta")
            table.add_column("Status", style="bold", width=6)
            table.add_column("Check", style="dim", width=20)
            table.add_column("Blocking", width=8)
            table.add_column("Message")

            for check in checks:
                status_style = {
                    "ok": "[green]ok[/green]",
                    "warn": "[yellow]warn[/yellow]",
                    "fail": "[red]fail[/red]",
                }.get(check.status, check.status)
                blocking_text = "yes" if check.blocking else "no"
                table.add_row(status_style, check.name, blocking_text, check.message)

            console.print(table)

            # Interactive fixes for blocking failures
            for check in checks:
                if check.blocking and check.status == "fail":
                    console.print(
                        Panel(
                            f"[bold red]{check.name}[/bold red]: {check.message}",
                            title="Blocking Failure",
                        )
                    )
                    fix_result = None
                    if check.name == "docker":
                        answer = click.prompt("Attempt to fix docker? (y/N)", default="N", show_default=False)
                        if answer.lower() == "y":
                            fix_result = attempt_fix_docker()
                    elif check.name == "cloudflared_cli":
                        answer = click.prompt("Attempt to fix cloudflared? (y/N)", default="N", show_default=False)
                        if answer.lower() == "y":
                            fix_result = attempt_fix_cloudflared()
                    elif check.name == "public_ports":
                        owners = process_owners_for_ports()
                        console.print("[bold yellow]Port ownership:[/bold yellow]")
                        for port, info in owners.items():
                            console.print(f"  {port}: {info}")
                    else:
                        console.print(f"[dim]No auto-fix available for {check.name}.[/dim]")

                    if fix_result:
                        console.print(f"[bold cyan]Fix result:[/bold cyan] {fix_result}")

            # Re-run checks after fixes
            console.print("\n[bold green]Re-running checks...[/bold green]")
            checks = run_checks(state)
            table = Table(title="Updated Results", show_header=True, header_style="bold magenta")
            table.add_column("Status", style="bold", width=6)
            table.add_column("Check", style="dim", width=20)
            table.add_column("Blocking", width=8)
            table.add_column("Message")
            for check in checks:
                status_style = {
                    "ok": "[green]ok[/green]",
                    "warn": "[yellow]warn[/yellow]",
                    "fail": "[red]fail[/red]",
                }.get(check.status, check.status)
                blocking_text = "yes" if check.blocking else "no"
                table.add_row(status_style, check.name, blocking_text, check.message)
            console.print(table)
        else:
            for check in checks:
                click.echo(f"[{check.status}] {check.name}: {check.message}")
            click.echo(summary_text(checks))

    fail_count = sum(1 for c in checks if c.status == "fail")
    if fail_count > 0:
        ctx.exit(1)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Print deployment status and resume point."""
    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    if not state.is_confirmed():
        console.print(
            "[yellow]No confirmed deployment state found. Run `rakkib init` to start.[/yellow]"
        )
        return

    from rich.table import Table

    table = Table(title="Rakkib Deployment Status", show_header=False)
    table.add_column("Key", style="bold cyan", width=20)
    table.add_column("Value")

    table.add_row("Confirmed", "yes")
    table.add_row("Resume Phase", str(state.resume_phase()))
    table.add_row("Domain", state.get("domain", "—") or "—")
    table.add_row("Data Root", state.get("data_root", "/srv") or "/srv")
    table.add_row("Platform", state.get("platform", "—") or "—")

    foundation = state.get("foundation_services") or []
    table.add_row("Foundation Services", ", ".join(foundation) if isinstance(foundation, list) else str(foundation))

    selected = state.get("selected_services") or []
    table.add_row("Selected Services", ", ".join(selected) if isinstance(selected, list) else str(selected))

    addons = state.get("host_addons") or []
    table.add_row("Host Addons", ", ".join(addons) if isinstance(addons, list) else str(addons))

    subdomains = state.get("subdomains") or {}
    if isinstance(subdomains, dict) and subdomains:
        subdomain_lines = "\n".join(f"  {svc}: {sub}" for svc, sub in subdomains.items())
        table.add_row("Subdomains", subdomain_lines)
    else:
        table.add_row("Subdomains", "—")

    console.print(table)


@cli.command()
@click.argument("service")
@click.pass_context
def add(ctx: click.Context, service: str) -> None:
    """Add a service to an existing deployment."""
    console.print(f"[bold green]Rakkib add {service}[/bold green]")

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    registry = services_step._load_registry()
    by_id = {s["id"]: s for s in registry["services"]}

    # 1. Validate service slug
    if service not in by_id:
        console.print(f"[bold red]Error:[/bold red] Service '{service}' not found in registry.")
        sys.exit(1)

    svc = by_id[service]
    state_bucket = svc.get("state_bucket", "selected_services")

    # 2. Check if already deployed
    if state_bucket == "always":
        console.print(f"[yellow]Service '{service}' is always deployed.[/yellow]")
        return

    foundation = set(state.get("foundation_services", []) or [])
    selected = set(state.get("selected_services", []) or [])

    if service in foundation or service in selected:
        console.print(f"[yellow]Service '{service}' is already deployed.[/yellow]")
        return

    # 3. Handle dependencies
    missing_deps = []
    for dep in svc.get("depends_on", []):
        dep_svc = by_id.get(dep, {})
        dep_bucket = dep_svc.get("state_bucket", "selected_services")
        if dep_bucket == "always":
            continue
        if dep not in foundation and dep not in selected:
            missing_deps.append(dep)

    if missing_deps:
        console.print(
            f"[bold red]Error:[/bold red] Missing dependencies for '{service}': {', '.join(missing_deps)}"
        )
        sys.exit(1)

    # 4. Prompt for subdomain customization
    default_subdomain = svc.get("default_subdomain")
    if default_subdomain:
        subdomain = click.prompt(
            f"Subdomain for {service}?",
            default=default_subdomain,
        )
        if not re.match(r"^[a-z0-9-]+$", subdomain):
            console.print(
                f"[bold red]Error:[/bold red] Subdomain must match ^[a-z0-9-]+$"
            )
            sys.exit(1)
        state.set(f"subdomains.{service}", subdomain)
        # Also set top-level alias so templates resolve {{SERVICE_SUBDOMAIN}}
        placeholder = svc.get("subdomain_placeholder")
        if placeholder:
            state.set(placeholder, subdomain)

    # 5. Update state
    if state_bucket == "foundation_services":
        current = list(state.get("foundation_services", []) or [])
        current.append(service)
        state.set("foundation_services", current)
    else:
        current = list(state.get("selected_services", []) or [])
        current.append(service)
        state.set("selected_services", current)

    state.save(state_path)
    console.print(f"[dim]Added {service} to {state_bucket}.[/dim]")

    # 6. Generate missing secrets
    services_step._generate_missing_secrets(state)
    state.save(state_path)

    # 7. Run Step 60 for just this service
    services_step.run_single_service(state, service)
    console.print(f"[bold green]Service {service} deployed successfully.[/bold green]")

    # 8. Update README.md
    _update_readme_agent_memory(repo_dir, state)
    console.print(f"[dim]Updated README.md with deployed services.[/dim]")


@cli.command()
@click.confirmation_option(prompt="Remove the rakkib CLI shim and PATH entries?")
def uninstall() -> None:
    """Remove the user-scoped rakkib command shim and managed PATH blocks."""
    target = Path.home() / ".local" / "bin" / "rakkib"
    if target.is_symlink():
        target.unlink()
        console.print(f"[green]Removed rakkib CLI shim at {target}[/green]")
    elif target.exists():
        console.print(f"[yellow]{target} exists but is not a symlink; not removed[/yellow]")
    else:
        console.print(f"[yellow]No rakkib CLI shim found at {target}[/yellow]")

    marker = "# Added by Rakkib: user-local bin on PATH"
    profiles = [
        Path.home() / ".bashrc",
        Path.home() / ".zshrc",
        Path.home() / ".profile",
    ]
    removed_any = False
    for profile in profiles:
        if not profile.exists():
            continue
        content = profile.read_text()
        if marker not in content:
            continue
        lines = content.splitlines()
        new_lines: list[str] = []
        skipping = False
        for line in lines:
            if line == marker:
                skipping = True
                continue
            if skipping and line == "esac":
                skipping = False
                continue
            if skipping:
                continue
            new_lines.append(line)
        # Preserve single trailing newline
        profile.write_text("\n".join(new_lines).rstrip() + "\n")
        console.print(f"[green]Removed managed PATH block from {profile}[/green]")
        removed_any = True

    if not removed_any:
        console.print("[yellow]No managed PATH block found in shell profiles[/yellow]")

    console.print(
        "\n[bold]Rakkib CLI shim uninstall is complete.[/bold]\n"
        "If this terminal still resolves rakkib, refresh your shell command cache or open a new terminal:\n"
        "  hash -r"
    )


@cli.command()
@click.argument("topic", default="sudo")
@click.pass_context
def auth(ctx: click.Context, topic: str) -> None:
    """Validate sudo readiness."""
    if topic not in ("sudo", "-h", "--help", ""):
        console.print(f"[red]Unknown auth topic: {topic}[/red]")
        ctx.exit(1)

    if topic in ("-h", "--help", ""):
        click.echo("Usage: rakkib auth sudo\n\nValidates sudo for this terminal with sudo -v.")
        return

    if os.geteuid() == 0:
        console.print("[green]Already running as root; no sudo validation needed.[/green]")
        return

    if shutil.which("sudo") is None:
        console.print("[red]sudo is required for privileged setup actions on Linux.[/red]")
        ctx.exit(1)

    console.print("[dim]Validating sudo for this terminal. Rakkib will not store your password.[/dim]")
    result = subprocess.run(["sudo", "-v"], capture_output=True, text=True)
    if result.returncode == 0:
        console.print("[green]Sudo is ready for this terminal according to your system sudo policy.[/green]")
    else:
        console.print("[red]Sudo validation failed. Run `sudo -v` in your terminal first.[/red]")
        ctx.exit(1)


@cli.group()
@click.pass_context
def privileged(ctx: click.Context) -> None:
    """Root-only helper actions."""
    if os.geteuid() != 0:
        console.print("[bold red]Error:[/bold red] This helper must be run with sudo or from a root shell.")
        ctx.exit(1)


@privileged.command(name="check")
def privileged_check() -> None:
    """Verify the helper is running as root."""
    console.print("[green]Privileged helper is running as root.[/green]")


@privileged.command(name="ensure-layout")
@click.option("--state", "state_path", type=click.Path(path_type=Path), default=".fss-state.yaml")
@click.option("--data-root", type=str, default="")
@click.option("--admin-user", type=str, default="")
@click.pass_context
def privileged_ensure_layout(
    ctx: click.Context, state_path: Path, data_root: str, admin_user: str
) -> None:
    """Create the base Rakkib data directories."""
    state = State.load(state_path)
    if not data_root:
        data_root = state.get("data_root") or "/srv"
    user = _resolve_admin_user(state, admin_user)

    console.print(f"[bold green]Creating Rakkib layout under {data_root}[/bold green]")
    paths = [
        Path(data_root),
        Path(data_root) / "docker",
        Path(data_root) / "data",
        Path(data_root) / "apps" / "static",
        Path(data_root) / "backups",
        Path(data_root) / "MDs",
    ]
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)
        shutil.chown(p, user=user, group=None)
        # Recursively chown for existing contents
        for root, dirs, files in os.walk(p):
            for d in dirs:
                shutil.chown(os.path.join(root, d), user=user, group=None)
            for f in files:
                shutil.chown(os.path.join(root, f), user=user, group=None)
    console.print(f"[green]Layout created and owned by {user}.[/green]")


@privileged.command(name="fix-repo-owner")
@click.option("--state", "state_path", type=click.Path(path_type=Path), default=".fss-state.yaml")
@click.option("--admin-user", type=str, default="")
@click.option("--repo-dir", type=click.Path(path_type=Path), default="")
@click.pass_context
def privileged_fix_repo_owner(
    ctx: click.Context, state_path: Path, admin_user: str, repo_dir: Path
) -> None:
    """Assign the repo back to the admin user."""
    state = State.load(state_path)
    user = _resolve_admin_user(state, admin_user)
    if not repo_dir:
        repo_dir = ctx.obj["repo_dir"]
    if not repo_dir.exists():
        console.print(f"[red]Repo directory does not exist: {repo_dir}[/red]")
        ctx.exit(1)

    console.print(f"[bold green]Assigning {repo_dir} to {user}[/bold green]")
    for root, dirs, files in os.walk(repo_dir):
        for d in dirs:
            shutil.chown(os.path.join(root, d), user=user, group=None)
        for f in files:
            shutil.chown(os.path.join(root, f), user=user, group=None)
    shutil.chown(repo_dir, user=user, group=None)
    console.print(f"[green]Repo ownership updated to {user}.[/green]")


@cli.command()
@click.pass_context
def prompt(ctx: click.Context) -> None:
    """Print the canonical installer prompt."""
    console.print(
        "\n[bold]Rakkib is ready for the agent-driven install flow.[/bold]\n"
        f"\nRepo path:\n  {ctx.obj['repo_dir']}\n"
        "\nPaste this prompt if your agent was not launched automatically:\n"
        "\n--- PROMPT START ---\n"
        "Read AGENT_PROTOCOL.md first.\n"
        "Use this repo as the installer.\n"
        "Ask me the question files in order.\n"
        "Record answers in .fss-state.yaml.\n"
        "Do not write outside the repo until Phase 6 (questions/06-confirm.md).\n"
        "Run the agent as the normal admin user. On Linux, do not run the full agent session as root; after confirmation, request sudo only for specific privileged setup actions.\n"
        "For privileged commands, use sudo -n so expired authorization fails fast instead of hanging for a password inside the agent session.\n"
        "After confirmation, execute the numbered files in steps/ in order. Run docs/runbooks/restore-test.md only if restore testing is explicitly requested.\n"
        "Stop on any failed Verify block and fix it before continuing.\n"
        "--- PROMPT END ---\n"
    )


def main() -> None:
    """Entrypoint for the rakkib CLI."""
    cli()


if __name__ == "__main__":
    main()
