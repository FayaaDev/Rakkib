"""Docker helpers — compose up/pull, health polling, log capture.

Design rule from pyplan.md: Docker output redirects to
${DATA_ROOT}/logs/<step>.log so no LLM watches the stream.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal


def compose_up(
    project_dir: Path | str,
    profiles: list[str] | None = None,
    services: list[str] | None = None,
    log_path: Path | str | None = None,
    detach: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run docker compose up for the given project directory."""
    cmd = ["docker", "compose", "--project-directory", str(project_dir)]
    if profiles:
        for profile in profiles:
            cmd.extend(["--profile", profile])
    cmd.append("up")
    if detach:
        cmd.append("-d")
    if services:
        cmd.extend(services)

    return _run(cmd, log_path=log_path)


def compose_pull(
    project_dir: Path | str,
    services: list[str] | None = None,
    log_path: Path | str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run docker compose pull for the given project directory."""
    cmd = ["docker", "compose", "--project-directory", str(project_dir), "pull"]
    if services:
        cmd.extend(services)
    return _run(cmd, log_path=log_path)


def compose_down(
    project_dir: Path | str,
    volumes: bool = False,
    log_path: Path | str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run docker compose down for the given project directory."""
    cmd = ["docker", "compose", "--project-directory", str(project_dir), "down"]
    if volumes:
        cmd.append("--volumes")
    return _run(cmd, log_path=log_path)


def health_check(
    container_name: str,
    timeout: int = 60,
) -> bool:
    """Poll docker container health status until healthy or timeout."""
    # TODO: implement polling loop using docker inspect
    return True


def _run(
    cmd: list[str],
    log_path: Path | str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command, optionally redirecting stdout/stderr to a log file."""
    if log_path:
        log_file = Path(log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a") as fh:
            return subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, text=True)
    return subprocess.run(cmd, capture_output=True, text=True)
