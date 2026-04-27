"""State management — .fss-state.yaml load, save, merge, and resume detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

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

    def set(self, key: str, value: Any) -> None:
        """Dot-notated write, creating intermediate dicts as needed."""
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value

    def merge(self, other: dict[str, Any]) -> None:
        """Deep-merge another dict into this state."""
        _deep_merge(self._data, other)

    def is_confirmed(self) -> bool:
        """Return True if the user has confirmed past Phase 6."""
        return bool(self.get("confirmed", False))

    def resume_phase(self) -> int:
        """Return the first phase (1-6) with missing required fields, or 7 if complete."""
        # TODO: implement resume logic after schema.py is ready (Wave 1)
        return 1

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
