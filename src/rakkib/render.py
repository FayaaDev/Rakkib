"""Template rendering — placeholder substitution from state -> template files.

Follows lib/placeholders.md rules:
- {{PLACEHOLDER}} syntax for direct string substitution
- Nested state values must be flattened before substitution
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jinja2 import Template

from rakkib.state import State

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_][A-Z0-9_]*)\}\}")


def flatten_state(state: State) -> dict[str, str]:
    """Flatten nested state keys into placeholder names."""
    flat: dict[str, str] = {}
    data = state.to_dict()
    _flatten("", data, flat)
    return flat


def _flatten(prefix: str, node: Any, out: dict[str, str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            _flatten(new_prefix, value, out)
    elif isinstance(node, list):
        # Store as newline-joined string for multiline placeholders
        out[prefix.upper()] = "\n".join(str(x) for x in node)
    else:
        out[prefix.upper()] = str(node) if node is not None else ""


def render_string(template_text: str, context: dict[str, str]) -> str:
    """Substitute placeholders in a template string."""
    # Use Jinja2 for robust substitution; our placeholders map to {{KEY}}
    # but Jinja2 expects {{ key }} or {{key}}.
    # We pre-process to ensure compatibility.
    return Template(template_text).render(**context)


def render_file(src: Path | str, dst: Path | str, state: State) -> None:
    """Render a template file to a destination path."""
    src_path = Path(src)
    dst_path = Path(dst)
    context = flatten_state(state)
    rendered = render_string(src_path.read_text(), context)
    dst_path.write_text(rendered)
