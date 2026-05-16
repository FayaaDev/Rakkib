"""Shared config models for the Rakkib web runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WebRuntimeConfig:
    """Configuration for the local ASGI web server."""

    host: str
    port: int
    repo_dir: Path
    token_auth_enabled: bool
    startup_token: str | None
