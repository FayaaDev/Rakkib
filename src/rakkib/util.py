"""Small shared utilities used by CLI and setup steps."""

from __future__ import annotations

import getpass
import os
import socket
from pathlib import Path


RAKKIB_DATA_DIR = Path(__file__).resolve().parent / "data"


def resolve_user(state=None, *, explicit: str | None = None, require: bool = False) -> str | None:
    """Resolve the admin/shell user from explicit input, state, sudo, or login."""
    if explicit:
        return explicit
    if state is not None:
        user = state.get("admin_user")
        if user:
            return str(user)
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user and sudo_user != "root":
        return sudo_user
    user = getpass.getuser()
    if user or not require:
        return user or None
    return None


def detect_lan_ip() -> str | None:
    """Best-effort detection of the primary LAN IP for URL printing."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
    except OSError:
        return None


def web_url(host: str, port: int, token: str | None) -> str:
    """Build the browser URL shown to the user."""
    base = f"http://{host}:{port}/"
    if not token:
        return base
    return f"{base}?token={token}"


def checkout_dir(repo_dir: Path) -> Path:
    """Resolve the git checkout root from either the repo root or package dir."""
    candidates = [repo_dir, repo_dir.parent.parent]
    for candidate in candidates:
        if (candidate / ".git").exists():
            return candidate
    return repo_dir
