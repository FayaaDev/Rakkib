"""State management — .fss-state.yaml load, save, merge, and resume detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from rakkib.schema import load_all_schemas

DEFAULT_STATE_FILE = ".fss-state.yaml"


class State:
    """In-memory representation of .fss-state.yaml."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @classmethod
    def load(cls, path: Path | str = DEFAULT_STATE_FILE) -> "State":
        """Load state from YAML file, returning an empty State if missing."""
        path = Path(path)
        if not path.exists():
            return cls({})
        raw = yaml.safe_load(path.read_text()) or {}
        return cls(raw)

    def save(self, path: Path | str = DEFAULT_STATE_FILE) -> None:
        """Persist state to YAML file."""
        path = Path(path)
        path.write_text(yaml.safe_dump(self._data, sort_keys=False, allow_unicode=True))

    def get(self, key: str, default: Any = None) -> Any:
        """Dot-notated read, e.g. get('cloudflare.tunnel_uuid')."""
        parts = key.split(".")
        node = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def has(self, key: str) -> bool:
        """Return True if the dot-notated key exists in state (even if value is None)."""
        parts = key.split(".")
        node = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return True

    def set(self, key: str, value: Any) -> None:
        """Dot-notated write, creating intermediate dicts as needed."""
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value

    def delete(self, key: str) -> None:
        """Delete a dot-notated key if it exists."""
        parts = key.split(".")
        node = self._data
        parents: list[tuple[dict[str, Any], str]] = []

        for part in parts[:-1]:
            if not isinstance(node, dict) or part not in node:
                return
            parents.append((node, part))
            node = node[part]

        if not isinstance(node, dict) or parts[-1] not in node:
            return

        del node[parts[-1]]

        for parent, child_key in reversed(parents):
            child = parent.get(child_key)
            if isinstance(child, dict) and not child:
                del parent[child_key]
            else:
                break

    def merge(self, other: dict[str, Any]) -> None:
        """Deep-merge another dict into this state."""
        _deep_merge(self._data, other)

    def is_confirmed(self) -> bool:
        """Return True if the user has confirmed past Phase 6."""
        return bool(self.get("confirmed", False))

    def resume_phase(self) -> int:
        """Return the first phase (1-6) with missing required fields, or 7 if complete."""
        schemas = load_all_schemas()
        for schema in schemas:
            if not self.is_phase_complete(schema.phase):
                return schema.phase
        return 7

    def is_phase_complete(self, phase: int) -> bool:
        """Return True if all required fields for the given phase have values in state."""
        schemas = load_all_schemas()
        schema = next((s for s in schemas if s.phase == phase), None)
        if schema is None:
            return False

        for field in schema.fields:
            if field.required is False:
                continue
            if field.type == "summary":
                continue
            if field.when and not _eval_when(field.when, self):
                continue
            for record_key in field.records:
                if not self.has(record_key):
                    return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """Return a shallow copy of the underlying data."""
        return dict(self._data)


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> None:
    """Merge overlay into base in-place, recursing into dicts."""
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _eval_when(condition: str, state: State) -> bool:
    """Evaluate a simple when condition against current state."""
    condition = condition.strip()
    if not condition:
        return True

    # Handle 'and' conjunctions (no 'or' in current schemas)
    if " and " in condition:
        parts = condition.split(" and ")
        return all(_eval_when(p.strip(), state) for p in parts)

    # Handle 'is null' / 'is not null'
    if " is not null" in condition:
        key = condition.replace(" is not null", "").strip()
        return state.get(key) is not None
    if " is null" in condition:
        key = condition.replace(" is null", "").strip()
        return state.get(key) is None

    # Handle 'in' (value in key, where key is a list)
    if " in " in condition:
        value, key = condition.split(" in ", 1)
        value = value.strip().strip("\"'")
        actual = state.get(key.strip())
        return isinstance(actual, list) and value in actual

    # Handle '=='
    if " == " in condition:
        key, value = condition.split(" == ", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        actual = state.get(key)
        return _coerce_compare(actual, value)

    # Handle '!='
    if " != " in condition:
        key, value = condition.split(" != ", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        actual = state.get(key)
        return not _coerce_compare(actual, value)

    return False


def _coerce_compare(actual: Any, expected: str) -> bool:
    """Compare a state value to an expected string, coercing booleans."""
    if isinstance(actual, bool):
        return str(actual).lower() == expected.lower()
    if actual is None:
        return expected.lower() == "none"
    return str(actual) == expected


def subdomain_placeholder_key(slug: str) -> str:
    """Return the state key used to store a service's subdomain placeholder."""
    return f"{slug.upper().replace('-', '_')}_SUBDOMAIN"
