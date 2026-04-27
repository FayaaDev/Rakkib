"""Interview engine — phase loop: prompt -> validate -> normalize -> persist."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Confirm, Prompt

from rakkib.schema import FieldDef, QuestionSchema, load_all_schemas
from rakkib.state import State

console = Console()


def run_interview(state: State, questions_dir: Path | str = "questions") -> State:
    """Drive Phases 1-6 using embedded AgentSchema blocks.

    Resume is automatic: load state, find first phase with unset required keys,
    start there. If ``confirmed: true``, ask once whether to start over.
    """
    schemas = load_all_schemas(questions_dir)
    if state.is_confirmed():
        overwrite = Confirm.ask(
            "An existing confirmed state was found. Start over?",
            default=False,
        )
        if overwrite:
            state = State({})

    for schema in schemas:
        _run_phase(schema, state)

    return state


def _run_phase(schema: QuestionSchema, state: State) -> None:
    """Execute a single phase's field list against the current state."""
    console.print(f"[bold blue]Phase {schema.phase}[/bold blue]")
    for field in schema.fields:
        _run_field(field, state)


def _run_field(field: FieldDef, state: State) -> None:
    """Process one field: detect, derive, prompt, validate, normalize, record."""
    # TODO: implement full field logic (Wave 1)
    # 1. Skip if `when` condition is false
    # 2. If `detect` is present, run command and normalize
    # 3. If `derive_from` is present, compute derived value
    # 4. Otherwise, prompt user (rich Prompt / Confirm)
    # 5. Validate input
    # 6. Normalize input
    # 7. Record into state per `records`
    pass


def _should_skip(field: FieldDef, state: State) -> bool:
    """Evaluate a `when` clause against current state."""
    if not field.when:
        return False
    # TODO: parse simple boolean expressions like "platform == linux"
    return False
