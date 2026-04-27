"""TUI prompt wrappers — questionary-based interactive prompts.

This module decouples interview.py and agent_handoff.py from the specific
prompt library (questionary), making tests easier to mock and allowing
future prompt library swaps with minimal changes.
"""

from __future__ import annotations

from typing import Any

import questionary
from questionary import Choice

from rich.console import Console

console = Console()


def prompt_text(message: str, default: str | None = None) -> str:
    """Ask the user for free-form text input.

    Falls back to a simple input() if questionary is unavailable
    (e.g., in non-TTY environments like CI).
    """
    kwargs: dict[str, Any] = {"message": message}
    if default is not None:
        kwargs["default"] = default
    result = questionary.text(**kwargs).ask()
    if result is None:
        return default if default is not None else ""
    return result


def prompt_confirm(message: str, default: bool = False) -> bool:
    """Ask the user a yes/no confirmation question.

    Uses questionary.select with Yes/No choices for modern arrow-key navigation.
    """
    choices: list[Choice] = [
        Choice(title="Yes", value=True),
        Choice(title="No", value=False),
    ]
    default_choice: Choice = choices[0] if default else choices[1]
    result = questionary.select(message=message, choices=choices, default=default_choice).ask()
    if result is None:
        return default
    return bool(result)


def prompt_select(message: str, choices: list[str | Choice], default: str | None = None) -> str | None:
    """Ask the user to select exactly one item from a list.

    Returns the selected value, or None if cancelled.
    """
    result = questionary.select(message=message, choices=choices, default=default).ask()
    return result


def prompt_checkbox(
    message: str,
    choices: list[Choice],
) -> list[str]:
    """Ask the user to select multiple items from a list.

    Returns a list of selected values. Returns empty list if cancelled.
    """
    result = questionary.checkbox(message=message, choices=choices).ask()
    return result if result is not None else []


def prompt_password(message: str) -> str:
    """Ask the user for a password (hidden input)."""
    result = questionary.password(message=message).ask()
    if result is None:
        return ""
    return result