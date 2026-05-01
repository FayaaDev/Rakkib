"""Rakkib CLI entrypoint.

Commands: init, pull, doctor, status, add, restart, uninstall, privileged, auth
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import click
from questionary import Choice
from rich.console import Console

from rakkib.docker import DockerError, docker_run
from rakkib.doctor import (
    attempt_fix_cloudflared,
    attempt_fix_compose,
    attempt_fix_docker,
    check_disk,
    check_ram,
    process_owners_for_ports,
    run_checks,
    summary_text,
    to_json,
)
from rakkib.interview import run_interview
from rakkib.state import State
from rakkib.steps import STEP_MODULES, VerificationResult, selected_service_defs
from rakkib.steps import postgres as postgres_step
from rakkib.steps import services as services_step
from rakkib.steps.cloudflare import _cloudflared_bin
from rakkib.tui import progress_spinner, prompt_checkbox, prompt_confirm

console = Console()


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


def _service_label(svc: dict[str, Any]) -> str:
    notes = str(svc.get("notes", "")).strip()
    summary = notes.split(".", 1)[0].strip()
    return f"{svc['id']} - {summary}" if summary else svc["id"]


def _service_selection_category(svc: dict[str, Any]) -> str:
    homepage = svc.get("homepage") or {}
    category = str(homepage.get("category") or "").strip()
    return category or "Other"


def _installed_service_ids(state: State) -> set[str]:
    installed = set(state.get("foundation_services", []) or [])
    installed.update(state.get("selected_services", []) or [])
    return installed


def _build_add_choices(state: State, registry: dict[str, Any]) -> list[Choice]:
    current = _installed_service_ids(state)

    choices: list[Choice] = []
    sections = [
        ("Always Installed", "always"),
        ("Foundation Bundle", "foundation_services"),
    ]

    for title, bucket in sections:
        bucket_services = [
            svc for svc in registry["services"] if svc.get("state_bucket") == bucket
        ]
        if not bucket_services:
            continue
        choices.append(
            Choice(title=f"━━ {title} ━━", value=f"__header_{bucket}__", disabled=True)
        )
        for svc in bucket_services:
            checked = bucket == "always" or svc["id"] in current
            disabled = bucket == "always"
            choices.append(
                Choice(
                    title=f"  {_service_label(svc)}",
                    value=svc["id"],
                    checked=checked,
                    disabled=disabled,
                )
            )

    optional_services = [
        svc for svc in registry["services"] if svc.get("state_bucket") == "selected_services"
    ]
    optional_groups: dict[str, list[dict[str, Any]]] = {}
    for svc in optional_services:
        optional_groups.setdefault(_service_selection_category(svc), []).append(svc)

    for category, services in optional_groups.items():
        choices.append(
            Choice(
                title=f"━━ {category} ━━",
                value=f"__header_{category}__",
                disabled=True,
            )
        )
        for svc in services:
            choices.append(
                Choice(
                    title=f"  {_service_label(svc)}",
                    value=svc["id"],
                    checked=svc["id"] in current,
                )
            )

    return choices


def _validate_service_dependencies(selected_ids: set[str], registry: dict[str, Any]) -> list[str]:
    by_id = {svc["id"]: svc for svc in registry["services"]}
    errors: list[str] = []

    for svc_id in sorted(selected_ids):
        svc = by_id[svc_id]
        missing = []
        for dep in svc.get("depends_on", []):
            dep_svc = by_id.get(dep, {})
            if dep_svc.get("state_bucket") == "always":
                continue
            if dep not in selected_ids:
                missing.append(dep)
        if missing:
            errors.append(f"{svc_id} requires {', '.join(missing)}")

    return errors


def _default_host_gateway(state: State) -> str:
    platform = str(state.get("platform", "linux")).lower()
    if platform == "mac":
        return "host.docker.internal"
    return "172.18.0.1"


def _apply_service_selection(state: State, registry: dict[str, Any], selected_ids: set[str]) -> None:
    active_ids = set(selected_ids)
    active_ids.update(
        svc["id"]
        for svc in registry["services"]
        if svc.get("state_bucket") == "always"
    )

    foundation_ids = [
        svc["id"]
        for svc in registry["services"]
        if svc.get("state_bucket") == "foundation_services" and svc["id"] in active_ids
    ]
    optional_ids = [
        svc["id"]
        for svc in registry["services"]
        if svc.get("state_bucket") == "selected_services" and svc["id"] in active_ids
    ]

    state.set("foundation_services", foundation_ids)
    state.set("selected_services", optional_ids)

    subdomains: dict[str, str] = {}
    current_subdomains = state.get("subdomains", {}) or {}
    secrets_values = dict(state.get("secrets.values", {}) or {})
    for svc in registry["services"]:
        svc_id = svc["id"]
        placeholder = svc.get("subdomain_placeholder")
        if svc_id not in active_ids:
            if placeholder:
                state.delete(placeholder)
            for key in (svc.get("secrets") or {}).keys():
                state.delete(key)
                secrets_values.pop(key, None)
            for condition in svc.get("conditional_secrets", []):
                for key in (condition.get("keys") or {}).keys():
                    state.delete(key)
                    secrets_values.pop(key, None)
            continue

        default_subdomain = svc.get("default_subdomain")
        if not default_subdomain:
            continue

        subdomain = current_subdomains.get(svc_id) or default_subdomain
        subdomains[svc_id] = subdomain
        if placeholder:
            state.set(placeholder, subdomain)

        if svc.get("host_service") and not state.get("host_gateway"):
            state.set("host_gateway", _default_host_gateway(state))

    state.set("subdomains", subdomains)
    state.set("secrets.values", secrets_values)


def _summarize_service_diff(added: list[str], removed: list[str]) -> None:
    if added:
        console.print(f"[green]Will install:[/green] {', '.join(added)}")
    if removed:
        console.print(f"[red]Will remove:[/red] {', '.join(removed)}")
        console.print("[yellow]Unchecked services will be fully purged, including data and service databases.[/yellow]")



def _check_docker() -> bool:
    """Verify docker and docker compose are available. Install if missing."""
    if shutil.which("docker") is None:
        with progress_spinner("Installing Docker..."):
            msg = attempt_fix_docker()
        console.print(f"[dim]{msg}[/dim]")
        if shutil.which("docker") is None:
            console.print("[bold red]Docker installation did not succeed. Aborting.[/bold red]")
            return False
        console.print("[green]Docker installed successfully.[/green]")

    compose_check = docker_run(["compose", "version"], check=False)
    if compose_check.returncode != 0:
        with progress_spinner("Installing Docker Compose plugin..."):
            msg = attempt_fix_compose()
        console.print(f"[dim]{msg}[/dim]")
        compose_check = docker_run(["compose", "version"], check=False)
        if compose_check.returncode != 0:
            console.print("[bold red]docker compose plugin installation did not succeed. Aborting.[/bold red]")
            return False
        console.print("[green]docker compose plugin installed successfully.[/green]")

    try:
        docker_run(["info"])
    except DockerError as exc:
        console.print(f"[bold red]Docker is installed but not usable by this shell:[/bold red] {exc}")
        return False

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
        with progress_spinner("Installing cloudflared..."):
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


def _print_deployed_urls(state: State, svc_ids: list[str] | None = None) -> None:
    domain = state.get("domain", "") or ""
    subdomains: dict[str, str] = state.get("subdomains", {}) or {}
    if not domain or not subdomains:
        return
    active_ids = set(svc_ids) if svc_ids is not None else _installed_service_ids(state)
    rows = [
        (svc_id, f"https://{subdomain}.{domain}")
        for svc_id, subdomain in subdomains.items()
        if subdomain and svc_id in active_ids
    ]
    if not rows:
        return
    console.print("\n[bold]Deployed services:[/bold]")
    for svc_id, url in rows:
        console.print(f"  [cyan]{svc_id}[/cyan]  {url}")


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
    _print_deployed_urls(state)
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

    domain = state.get("domain", "") or ""
    data_root = state.get("data_root", "/srv") or "/srv"

    console.print(f"\n[bold]Domain:[/bold] [cyan]{domain or '—'}[/cyan]")

    # System checks
    console.rule("[bold]System[/bold]")
    _icons = {"ok": "[green]✓[/green]", "warn": "[yellow]⚠[/yellow]", "fail": "[red]✗[/red]"}
    _colors = {"ok": "green", "warn": "yellow", "fail": "red"}
    for chk in (check_ram(), check_disk(data_root)):
        icon = _icons.get(chk.status, "?")
        color = _colors.get(chk.status, "white")
        console.print(f"  {icon}  [{color}]{chk.name.upper()}[/{color}]  {chk.message}")

    # Installed services
    console.rule("[bold]Installed Services[/bold]")
    registry = services_step._load_registry()
    subdomains: dict[str, str] = state.get("subdomains", {}) or {}
    foundation_ids = set(state.get("foundation_services", []) or [])
    selected_ids = set(state.get("selected_services", []) or [])
    installed_ids = foundation_ids | selected_ids

    for svc in registry["services"]:
        svc_id = svc["id"]
        bucket = svc.get("state_bucket", "")
        if bucket != "always" and svc_id not in installed_ids:
            continue
        subdomain = subdomains.get(svc_id)
        if subdomain and domain:
            console.print(f"  [cyan]{svc_id}[/cyan]  https://{subdomain}.{domain}")
        else:
            console.print(f"  [cyan]{svc_id}[/cyan]")

    # Available services
    console.rule("[bold]Available Services[/bold]")
    available = [
        svc for svc in registry["services"]
        if svc.get("state_bucket") in ("foundation_services", "selected_services")
        and svc["id"] not in installed_ids
    ]
    if available:
        for svc in available:
            console.print(f"  [dim]{svc['id']}[/dim]")
    else:
        console.print("  [dim]All available services are installed.[/dim]")
    console.print()


@cli.command()
@click.argument("service", required=False)
@click.pass_context
def add(ctx: click.Context, service: str | None) -> None:
    """Sync deployed services against the registry."""
    console.print("[bold green]Rakkib add[/bold green]")

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    registry = services_step._load_registry()
    old_selected = set(state.get("foundation_services", []) or [])
    old_selected.update(state.get("selected_services", []) or [])

    if service:
        by_id = {svc["id"]: svc for svc in registry["services"]}
        if service not in by_id:
            console.print(f"[bold red]Error:[/bold red] Unknown service '{service}'.")
            sys.exit(1)
        selected_ids = set(old_selected)
        if by_id[service].get("state_bucket") != "always":
            selected_ids.add(service)
    else:
        selected = prompt_checkbox(
            "Select services to keep installed:",
            choices=_build_add_choices(state, registry),
        )
        selected_ids = set(selected)

    dependency_errors = _validate_service_dependencies(selected_ids, registry)
    if dependency_errors:
        console.print("[bold red]Error:[/bold red] Invalid service selection:")
        for error in dependency_errors:
            console.print(f"  - {error}")
        sys.exit(1)

    added = sorted(selected_ids - old_selected)
    removed = sorted(old_selected - selected_ids)

    if added or removed:
        _summarize_service_diff(added, removed)
        if not prompt_confirm("Apply these service changes?", default=False):
            console.print("[yellow]Aborted.[/yellow]")
            return
    else:
        console.print("[yellow]No selection changes; refreshing selected services.[/yellow]")

    with progress_spinner("Applying service changes..."):
        removal_order = [
            svc["id"]
            for svc in reversed(selected_service_defs(state, registry))
            if svc["id"] in removed
        ]
        for svc_id in removal_order:
            services_step.remove_single_service(state, svc_id)

        _apply_service_selection(state, registry, selected_ids)
        services_step._generate_missing_secrets(state)
        state.save(state_path)

        postgres_step.run(state)
        if service:
            services_step.run_single_service(state, service)
        elif added:
            for svc_id in added:
                services_step.run_single_service(state, svc_id)
        else:
            # Removals-only or no changes — reload caddy to apply route changes and sync
            data_root = Path(state.get("data_root", "/srv"))
            services_step._reload_caddy(data_root)
            services_step.sync_shared_artifacts(
                state, services_step._repo_dir(), data_root, services_step._load_registry()
            )
        state.save(state_path)

    console.print("[bold green]Service selection synced successfully.[/bold green]")
    deployed_ids: list[str] | None = None
    if service:
        deployed_ids = [service]
    elif added:
        deployed_ids = list(added)
    if deployed_ids:
        _print_deployed_urls(state, deployed_ids)


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
    admin_dirs = [
        root / "docker",
        root / "apps" / "static",
        root / "backups",
        root / "MDs",
        root / "logs",
    ]
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
