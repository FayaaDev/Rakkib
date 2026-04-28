"""Template rendering — placeholder substitution from state -> template files.

- {{PLACEHOLDER}} syntax for direct string substitution
- Nested state values must be flattened before substitution
- Missing placeholders are left as-is (uses jinja2.DebugUndefined)
- Supports both {{PLACEHOLDER}} and Jinja2 {{ PLACEHOLDER }} style
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jinja2 import DebugUndefined, Environment

from rakkib.state import State

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_][A-Z0-9_]*)\}\}")
_env = Environment(undefined=DebugUndefined)


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
    """Substitute placeholders in a template string.

    Uses Jinja2 with :class:`jinja2.DebugUndefined` so missing placeholders
    are left as-is (e.g. ``{{ MISSING }}`` remains in the output) rather
    than raising an error or being silently removed.
    """
    return _env.from_string(template_text).render(**context)


def render_text(src_text: str, state: State) -> str:
    """Render a template string using flattened state as context."""
    context = flatten_state(state)
    return render_string(src_text, context)


def render_file(src: Path | str, dst: Path | str, state: State) -> None:
    """Render a template file to a destination path."""
    src_path = Path(src)
    dst_path = Path(dst)
    context = flatten_state(state)
    rendered = render_string(src_path.read_text(), context)
    dst_path.write_text(rendered)


def render_tree(src_dir: Path | str, dst_dir: Path | str, state: State) -> None:
    """Recursively render all ``.tmpl`` files in *src_dir* into *dst_dir*.

    Each ``.tmpl`` extension is stripped on output.  Directory structure
    is preserved.  Non-``.tmpl`` files are skipped.
    """
    src_path = Path(src_dir)
    dst_path = Path(dst_dir)
    context = flatten_state(state)

    for src_file in src_path.rglob("*.tmpl"):
        rel = src_file.relative_to(src_path)
        dst_file = dst_path / rel.with_suffix("")
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        rendered = render_string(src_file.read_text(), context)
        dst_file.write_text(rendered)
