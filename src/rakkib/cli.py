"""Rakkib CLI entrypoint.

Commands: init, doctor, status, add, uninstall
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from rakkib.agent_handoff import handoff
from rakkib.interview import run_interview
from rakkib.state import State
from rakkib.steps import VerificationResult

console = Console()


def _run_steps(
    state: State,
    repo_dir: Path,
    agent: str = "auto",
    print_prompt: bool = False,
    no_agent: bool = False,
) -> bool:
    """Execute setup steps in order. Return True if all pass."""
    steps: list[tuple[str, str]] = [
        ("10", "rakkib.steps.layout"),
        ("30", "rakkib.steps.caddy"),
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


@click.group()
@click.version_option(version=__import__("rakkib").__version__, prog_name="rakkib")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Rakkib — agent-driven personal server kit."""
    ctx.ensure_object(dict)
    if "repo_dir" not in ctx.obj:
        ctx.obj["repo_dir"] = Path(__file__).resolve().parent.parent.parent


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

    # Auto-resume if state is already confirmed
    if resume or state.is_confirmed():
        console.print("[dim]State is confirmed — resuming step execution.[/dim]")
        _run_steps(state, repo_dir, agent=agent, print_prompt=print_prompt, no_agent=no_agent)
        return

    state = run_interview(state, questions_dir=repo_dir / "questions")
    state.save(state_path)
    console.print("[bold green]Interview complete. State saved to .fss-state.yaml[/bold green]")

    if state.is_confirmed():
        _run_steps(state, repo_dir, agent=agent, print_prompt=print_prompt, no_agent=no_agent)
    else:
        console.print("[yellow]State is not confirmed — run `rakkib init` again to confirm and execute steps.[/yellow]")


@cli.command()
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Run host diagnostics."""
    console.print("[bold green]Rakkib doctor[/bold green]")
    # TODO: port scripts/rakkib-doctor logic into Python


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Print deployment status and resume point."""
    console.print("[bold green]Rakkib status[/bold green]")
    # TODO: read state, show deployed services + resume phase


@cli.command()
@click.argument("service")
@click.pass_context
def add(ctx: click.Context, service: str) -> None:
    """Add a service to an existing deployment."""
    console.print(f"[bold green]Rakkib add {service}[/bold green]")
    # TODO: run per-service wizard + Step 60 slice (Wave 5)


@cli.command()
@click.confirmation_option(prompt="Remove the rakkib CLI shim?")
def uninstall() -> None:
    """Remove the user-scoped rakkib command shim."""
    target = Path.home() / ".local" / "bin" / "rakkib"
    if target.is_symlink():
        target.unlink()
        console.print(f"[green]Removed {target}[/green]")
    elif target.exists():
        console.print(f"[yellow]{target} exists but is not a symlink; not removed[/yellow]")
    else:
        console.print(f"[yellow]No shim found at {target}[/yellow]")

    # TODO: remove managed PATH block from ~/.bashrc


@cli.command()
@click.pass_context
def auth(ctx: click.Context) -> None:
    """Validate sudo readiness."""
    console.print("[bold green]Rakkib auth[/bold green]")
    # TODO: sudo -v validation


def main() -> None:
    """Entrypoint for the rakkib CLI."""
    cli()


if __name__ == "__main__":
    main()
