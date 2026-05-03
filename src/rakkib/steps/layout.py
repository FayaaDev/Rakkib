"""Step 1 — Layout.

Create the target directory structure under ``DATA_ROOT``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from rakkib.state import State
from rakkib.steps import VerificationResult


def _service_ids(state: State) -> list[str]:
    """Return the union of required, foundation, and selected service IDs."""
    required = ["caddy", "cloudflared", "postgres"]
    foundation = state.get("foundation_services", []) or []
    selected = state.get("selected_services", []) or []
    return required + foundation + selected


def run(state: State) -> None:
    data_root = Path(state.get("data_root", "/srv"))
    admin_user = state.get("admin_user")
    platform = state.get("platform", "linux")
    services = _service_ids(state)

    dirs: list[Path] = [
        data_root,
        data_root / "docker",
        data_root / "data",
        data_root / "apps" / "static",
        data_root / "backups",
        data_root / "MDs",
        data_root / "logs",
    ]
    for svc in services:
        dirs.append(data_root / "docker" / svc)

    if platform == "linux" and os.geteuid() != 0:
        # Attempt password-less sudo for directory creation.
        result = subprocess.run(
            ["sudo", "-n", "mkdir", "-p"] + [str(d) for d in dirs],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "sudo authorization required to create layout directories. "
                "Please run `rakkib auth sudo` first."
            )

        # Set ownership to admin_user where applicable.
        if admin_user:
            for d in dirs:
                subprocess.run(
                    ["sudo", "-n", "chown", str(admin_user), str(d)],
                    capture_output=True,
                    text=True,
                )
    else:
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    # Write a simple log entry for idempotency tracking.
    log_path = data_root / "logs" / "layout.log"
    log_path.write_text("layout step completed\n")


def verify(state: State) -> VerificationResult:
    data_root = Path(state.get("data_root", "/srv"))
    dirs = [
        data_root / "docker",
        data_root / "data",
        data_root / "apps" / "static",
        data_root / "backups",
        data_root / "MDs",
        data_root / "logs",
    ]
    for d in dirs:
        if not d.exists():
            return VerificationResult.failure("layout", f"Directory {d} does not exist")
        if not os.access(d, os.W_OK):
            return VerificationResult.failure("layout", f"Directory {d} is not writable")
    return VerificationResult.success("layout", "Layout directories created")
