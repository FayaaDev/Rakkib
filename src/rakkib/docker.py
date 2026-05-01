"""Docker helpers — compose up/pull, health polling, log capture.

Design rule from pyplan.md: Docker output redirects to
${DATA_ROOT}/logs/<step>.log so no LLM watches the stream.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from rakkib.tui import progress_spinner


class DockerError(Exception):
    """Raised when a docker command fails."""

    def __init__(self, message: str, cmd: list[str], returncode: int, stderr: str = "") -> None:
        super().__init__(message)
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr


def _docker_timeout() -> int:
    raw = os.environ.get("RAKKIB_DOCKER_TIMEOUT", "3600")
    try:
        return int(raw)
    except ValueError:
        return 3600


def compose_up(
    project_dir: Path | str,
    profiles: list[str] | None = None,
    services: list[str] | None = None,
    log_path: Path | str | None = None,
    detach: bool = True,
    timeout: int | None = None,
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

    return _run(cmd, log_path=log_path, timeout=timeout, progress_message="Starting Docker services...")


def compose_pull(
    project_dir: Path | str,
    services: list[str] | None = None,
    log_path: Path | str | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run docker compose pull for the given project directory."""
    cmd = ["docker", "compose", "--project-directory", str(project_dir), "pull"]
    if services:
        cmd.extend(services)
    return _run(cmd, log_path=log_path, timeout=timeout, progress_message="Pulling Docker images...")


def compose_down(
    project_dir: Path | str,
    volumes: bool = False,
    log_path: Path | str | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run docker compose down for the given project directory."""
    cmd = ["docker", "compose", "--project-directory", str(project_dir), "down"]
    if volumes:
        cmd.append("--volumes")
    return _run(cmd, log_path=log_path, timeout=timeout, progress_message="Removing Docker services...")


def health_check(
    container_name: str,
    timeout: int = 60,
) -> bool:
    """Poll docker container health status until healthy or timeout.

    If the container has no healthcheck configured, fall back to checking
    whether the container is running.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = _run(
                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{.State.Health.Status}}",
                    container_name,
                ],
                check=False,
            )
            status = result.stdout.strip()
            # If status is empty, no healthcheck is configured; fall back.
            if not status or status == "<no value>":
                if container_running(container_name):
                    return True
            elif status == "healthy":
                return True
            elif status == "unhealthy":
                return False
        except DockerError:
            # Container may not exist yet
            pass
        time.sleep(2)
    return False


def container_running(container_name: str) -> bool:
    """Return True if the named container is running."""
    try:
        result = _run(
            [
                "docker",
                "inspect",
                "-f",
                "{{.State.Running}}",
                container_name,
            ],
            check=False,
        )
        return result.stdout.strip().lower() == "true"
    except DockerError:
        return False


def container_publishes_port(container_name: str, port: int) -> bool:
    """Return True if the container publishes the given host port."""
    try:
        result = _run(
            [
                "docker",
                "inspect",
                "-f",
                "{{json .NetworkSettings.Ports}}",
                container_name,
            ],
            check=False,
        )
        ports: dict[str, Any] = json.loads(result.stdout or "{}")
        for key, bindings in ports.items():
            if not key:
                continue
            container_port = key.split("/")[0]
            if int(container_port) == port:
                if bindings:
                    return True
        return False
    except (DockerError, json.JSONDecodeError, ValueError):
        return False


def network_exists(network_name: str) -> bool:
    """Return True if the docker network exists."""
    try:
        _run(["docker", "network", "inspect", network_name])
        return True
    except DockerError:
        return False


def capture_container_logs(container_name: str, log_path: Path | str, tail: int = 200) -> None:
    """Append the last *tail* lines of container logs to *log_path*."""
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail), container_name],
            capture_output=True,
            text=True,
        )
        with log_file.open("a") as fh:
            fh.write(f"\n--- logs: {container_name} (last {tail} lines) ---\n")
            fh.write(result.stdout)
            if result.stderr:
                fh.write(result.stderr)
    except Exception:
        pass


def create_network(network_name: str, driver: str = "bridge") -> None:
    """Create a docker network if it does not already exist."""
    if network_exists(network_name):
        return
    _run(["docker", "network", "create", "--driver", driver, network_name])


def _run(
    cmd: list[str],
    log_path: Path | str | None = None,
    check: bool = True,
    timeout: int | None = None,
    progress_message: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command, optionally redirecting stdout/stderr to a log file.

    When check is True (default), raises DockerError on non-zero exit codes.
    """
    effective_timeout = timeout if timeout is not None else _docker_timeout()
    log_file = Path(log_path) if log_path else None
    try:
        with progress_spinner(progress_message) if progress_message else nullcontext():
            if log_file:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                with log_file.open("a") as fh:
                    result = subprocess.run(
                        cmd,
                        stdout=fh,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=effective_timeout,
                    )
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=effective_timeout)
    except subprocess.TimeoutExpired as exc:
        log_hint = f" See log: {log_file}" if log_file else ""
        if log_file:
            with log_file.open("a") as fh:
                fh.write(f"\nCommand timed out after {effective_timeout}s: {' '.join(cmd)}\n")
        raise DockerError(
            message=f"Command timed out after {effective_timeout}s: {' '.join(cmd)}.{log_hint}",
            cmd=cmd,
            returncode=124,
            stderr=str(exc),
        ) from exc

    if check and result.returncode != 0:
        log_hint = f" See log: {log_file}" if log_file else ""
        raise DockerError(
            message=f"Command failed with exit code {result.returncode}: {' '.join(cmd)}.{log_hint}",
            cmd=cmd,
            returncode=result.returncode,
            stderr=result.stderr,
        )
    return result
