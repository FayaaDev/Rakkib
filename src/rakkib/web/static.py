"""Helpers for serving packaged web assets."""

from __future__ import annotations

from pathlib import Path

from rakkib.util import RAKKIB_DATA_DIR


def packaged_web_root() -> Path:
    """Return the directory containing built or placeholder web assets."""
    return RAKKIB_DATA_DIR / "web"


def packaged_index_path() -> Path:
    """Return the packaged SPA entrypoint path."""
    return packaged_web_root() / "index.html"


def resolve_packaged_file(request_path: str) -> Path | None:
    """Resolve a request path to a packaged asset, guarding against traversal."""
    root = packaged_web_root().resolve()
    candidate = (root / request_path.lstrip("/")).resolve()

    if candidate == root or root not in candidate.parents:
        return None
    if not candidate.is_file():
        return None
    return candidate
