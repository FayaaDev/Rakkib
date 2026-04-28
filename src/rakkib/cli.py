"""Rakkib CLI entrypoint.

Commands: init, pull, doctor, status, add, restart, uninstall, privileged, auth
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

from rakkib.doctor import (
    attempt_fix_cloudflared,
    attempt_fix_compose,
    attempt_fix_docker,
    process_owners_for_ports,
    run_checks,
    summary_text,
    to_json,
)
from rakkib.interview import run_interview
from rakkib.state import State
from rakkib.steps import STEP_MODULES, VerificationResult
from rakkib.steps import services as services_step
from rakkib.steps.cloudflare import _cloudflared_bin

console = Console()
_RX_SUBDOMAIN = re.compile(r"^[a-z0-9-]+$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _render_doctor_table(checks: list, title: str) -> "Table":
    from rich.table import Table
    table = Table(title=title, show_header=True, header_style="bold magenta")
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
        table.add_row(status_style, check.name, "yes" if check.blocking else "no", check.message)
    return table


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



def _check_docker() -> bool:
    """Verify docker and docker compose are available. Install if missing."""
    if shutil.which("docker") is None:
        console.print("[dim]Docker not found — installing automatically...[/dim]")
        msg = attempt_fix_docker()
        console.print(f"[dim]{msg}[/dim]")
        if shutil.which("docker") is None:
            console.print("[bold red]Docker installation did not succeed. Aborting.[/bold red]")
            return False
        console.print("[green]Docker installed successfully.[/green]")

    compose_check = subprocess.run(["docker", "compose", "version"],
                                   capture_output=True, text=True)
    if compose_check.returncode != 0:
        console.print("[dim]docker compose plugin not found — installing automatically...[/dim]")
        msg = attempt_fix_compose()
        console.print(f"[dim]{msg}[/dim]")
        compose_check = subprocess.run(["docker", "compose", "version"],
                                       capture_output=True, text=True)
        if compose_check.returncode != 0:
            console.print("[bold red]docker compose plugin installation did not succeed. Aborting.[/bold red]")
            return False
        console.print("[green]docker compose plugin installed successfully.[/green]")

    return True


def _ensure_prereqs() -> bool:
    """Install host prerequisites (Docker, cloudflared) if missing. Return False to abort."""
    if not _check_docker():
        return False

    local_cf = Path.home() / ".local" / "bin" / "cloudflared"
    cf_ok = local_cf.is_file()
    if not cf_ok:
        try:
            cf_ok = (
                subprocess.run([_cloudflared_bin(), "--version"], capture_output=True, text=True).returncode == 0
            )
        except FileNotFoundError:
            pass

    if not cf_ok:
        console.print("[dim]cloudflared not found — installing automatically...[/dim]")
        msg = attempt_fix_cloudflared()
        console.print(f"[dim]{msg}[/dim]")
        cf_ok = local_cf.is_file()
        if cf_ok:
            try:
                cf_ok = (
                    subprocess.run([str(local_cf), "--version"], capture_output=True, text=True).returncode == 0
                )
            except FileNotFoundError:
                cf_ok = False
        if not cf_ok:
            console.print(
                "[bold red]cloudflared installation failed. "
                "Install manually: https://github.com/cloudflare/cloudflared/releases[/bold red]"
            )
            return False

    return True


def _run_steps(state: State, repo_dir: Path) -> bool:
    """Execute setup steps in order. Return True if all pass."""
    all_steps = STEP_MODULES + [("verify", "rakkib.steps.verify")]
    verify_cache: dict[str, VerificationResult] = {}

    for step_name, module_path in all_steps:
        console.print(f"[bold green]Step {step_name}[/bold green]")
        try:
            module = __import__(module_path, fromlist=["run", "verify"])
            run_fn = getattr(module, "run", None)
            verify_fn = getattr(module, "verify", None)

            if run_fn is None:
                console.print(f"[yellow]  Step {step_name} module has no run() — skipping[/yellow]")
                continue

            if step_name == "verify":
                # Pass cached results so verify.run() can skip re-running each step verify.
                state.set("_step_verify_cache", {k: {"ok": v.ok, "step": v.step, "message": v.message} for k, v in verify_cache.items()})

            run_fn(state)

            if step_name == "verify":
                # verify.run() already ran _collect_verifications and printed the summary;
                # calling verify_fn again would triple-run each step's verify().
                break

            if verify_fn is not None:
                result = verify_fn(state)
                verify_cache[step_name] = result
                if not result.ok:
                    console.print(f"[bold red]  Step {step_name} verify failed:[/bold red] {result.message}")
                    if result.log_path:
                        console.print(f"[dim]  Log: {result.log_path}[/dim]")
                    return False
                console.print(f"[dim]  Step {step_name} verify passed[/dim]")
            else:
                console.print(f"[dim]  Step {step_name} has no verify() — skipping check[/dim]")

        except Exception as exc:
            console.print(f"[bold red]  Step {step_name} failed:[/bold red] {exc}")
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
    """Rakkib — personal server installer."""
    ctx.ensure_object(dict)
    if "repo_dir" not in ctx.obj:
        ctx.obj["repo_dir"] = Path(__file__).resolve().parent


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Gather configuration via interview and save to .fss-state.yaml.

    Run `rakkib pull` afterwards to install everything.
    """
    console.print("[bold green]Rakkib init[/bold green]")

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    state = run_interview(state, questions_dir=repo_dir / "data" / "questions")
    state.save(state_path)
    console.print("[bold green]Interview complete. State saved to .fss-state.yaml[/bold green]")

    if state.is_confirmed():
        console.print("[dim]Run [bold]rakkib pull[/bold] to install.[/dim]")
    else:
        console.print("[yellow]State is not confirmed — run `rakkib init` again to complete the interview.[/yellow]")


@cli.command()
@click.pass_context
def pull(ctx: click.Context) -> None:
    """Install prerequisites and run all setup steps.

    Requires a confirmed state from `rakkib init`.
    """
    console.print("[bold green]Rakkib pull[/bold green]")

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    if not state.is_confirmed():
        console.print(
            "[bold red]State is not confirmed.[/bold red] "
            "Run [bold]rakkib init[/bold] first."
        )
        return

    if not _ensure_prereqs():
        return

    _run_steps(state, repo_dir)


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

            console.print(_render_doctor_table(checks, "Rakkib Doctor"))

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
                        answer = click.prompt("Attempt to fix docker?", type=click.Choice(["y", "n"]), default="n", show_default=False)
                        if answer == "y":
                            fix_result = attempt_fix_docker()
                    elif check.name == "cloudflared_cli":
                        answer = click.prompt("Attempt to fix cloudflared?", type=click.Choice(["y", "n"]), default="n", show_default=False)
                        if answer == "y":
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
            console.print(_render_doctor_table(checks, "Updated Results"))
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
        if not _RX_SUBDOMAIN.match(subdomain):
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

    # 7. Run Step 5 for just this service
    services_step.run_single_service(state, service)
    console.print(f"[bold green]Service {service} deployed successfully.[/bold green]")


@cli.command()
@click.argument("service", required=False)
@click.option("--all", "restart_all", is_flag=True, help="Restart all services in dependency order")
@click.pass_context
def restart(ctx: click.Context, service: str | None, restart_all: bool) -> None:
    """Restart one or all deployed services.

    \b
    rakkib restart caddy          # restart a single service
    rakkib restart --all          # restart all services in dependency order
    """
    if not service and not restart_all:
        console.print("[yellow]Specify a service name or use --all.[/yellow]")
        ctx.exit(1)
    if service and restart_all:
        console.print("[yellow]Use either a service name or --all, not both.[/yellow]")
        ctx.exit(1)

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    if restart_all:
        console.print("[bold green]Restarting all services...[/bold green]")
        try:
            restarted = services_step.restart_all(state)
        except subprocess.CalledProcessError as exc:
            console.print(f"[bold red]Restart failed:[/bold red] {exc}")
            sys.exit(1)
        for svc_id in restarted:
            console.print(f"  [green]✓[/green] {svc_id}")
        console.print(f"[bold green]Done.[/bold green] {len(restarted)} service(s) restarted.")
    else:
        console.print(f"[bold green]Restarting {service}...[/bold green]")
        try:
            services_step.restart_service(state, service)
        except ValueError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)
        except subprocess.CalledProcessError as exc:
            console.print(f"[bold red]Restart failed:[/bold red] {exc}")
            sys.exit(1)
        console.print(f"[green]✓[/green] {service} restarted.")


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
    root = Path(data_root)
    # These dirs are admin-owned by design; recurse into them safely.
    admin_dirs = [root / "docker", root / "apps" / "static", root / "backups", root / "MDs"]
    # These dirs must be created but NOT recursed — data/ contains service-managed UIDs.
    top_only = [root, root / "apps", root / "data"]

    for p in admin_dirs + top_only:
        p.mkdir(parents=True, exist_ok=True)

    for p in top_only:
        shutil.chown(p, user=user, group=None)

    for p in admin_dirs:
        shutil.chown(p, user=user, group=None)
        for dirpath, dirs, files in os.walk(p):
            for d in dirs:
                shutil.chown(os.path.join(dirpath, d), user=user, group=None)
            for f in files:
                shutil.chown(os.path.join(dirpath, f), user=user, group=None)

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



def main() -> None:
    """Entrypoint for the rakkib CLI."""
    cli()


if __name__ == "__main__":
    main()
