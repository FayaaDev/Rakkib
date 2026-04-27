"""Rakkib CLI entrypoint.

Commands: init, doctor, status, add, uninstall
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
from rich.console import Console

from rakkib.interview import run_interview
from rakkib.state import State

console = Console()


@click.group()
@click.version_option(version=__import__("rakkib").__version__, prog_name="rakkib")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Rakkib — agent-driven personal server kit."""
    ctx.ensure_object(dict)
    ctx.obj["repo_dir"] = Path(__file__).resolve().parent.parent.parent


@cli.command()
@click.option("--agent", type=str, default="auto", help="Agent mode: auto, opencode, claude, codex, none")
@click.option("--print-prompt", is_flag=True, help="Print the agent prompt and exit")
@click.option("--no-agent", is_flag=True, help="Equivalent to --agent none")
@click.pass_context
def init(ctx: click.Context, agent: str, print_prompt: bool, no_agent: bool) -> None:
    """Run diagnostics and launch the setup wizard."""
    if no_agent:
        agent = "none"

    if agent != "auto":
        console.print(f"[dim]Note: --agent / --no-agent options are not yet implemented (requested: {agent}).[/dim]")
    if print_prompt:
        console.print("[dim]Note: --print-prompt is not yet implemented.[/dim]")

    console.print("[bold green]Rakkib init[/bold green]")

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)
    state = run_interview(state, questions_dir=repo_dir / "questions")
    state.save(state_path)
    console.print("[bold green]Interview complete. State saved to .fss-state.yaml[/bold green]")


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
