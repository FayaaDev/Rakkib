"""Step 30 — Caddy.

Render and deploy the base Caddy reverse proxy.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rakkib.render import render_file
from rakkib.state import State
from rakkib.steps import VerificationResult


def _repo_dir() -> Path:
    """Return the package data directory (contains ``templates/``)."""
    return Path(__file__).resolve().parent.parent / "data"


def run(state: State) -> None:
    data_root = Path(state.get("data_root", "/srv"))
    docker_net = state.get("docker_net", "caddy_net")
    caddy_dir = data_root / "docker" / "caddy"
    caddy_dir.mkdir(parents=True, exist_ok=True)
    (caddy_dir / "routes").mkdir(parents=True, exist_ok=True)

    log_path = data_root / "logs" / "caddy.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Create external docker network if it does not exist.
    net_check = subprocess.run(
        ["docker", "network", "inspect", docker_net],
        capture_output=True,
        text=True,
    )
    if net_check.returncode != 0:
        subprocess.run(
            ["docker", "network", "create", docker_net],
            capture_output=True,
            text=True,
            check=True,
        )

    repo = _repo_dir()

    # 2-5. Render pieces and concatenate into Caddyfile.next.
    header = caddy_dir / "Caddyfile.header"
    root_route = caddy_dir / "routes" / "root.caddy"
    footer = caddy_dir / "Caddyfile.footer"
    caddy_next = caddy_dir / "Caddyfile.next"

    render_file(repo / "templates" / "caddy" / "Caddyfile.header.tmpl", header, state)
    render_file(repo / "templates" / "caddy" / "routes" / "root.caddy.tmpl", root_route, state)
    render_file(repo / "templates" / "caddy" / "Caddyfile.footer.tmpl", footer, state)

    caddy_next.write_text(
        header.read_text() + "\n" + root_route.read_text() + "\n" + footer.read_text()
    )

    # 6a. Format the candidate Caddyfile.
    subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{caddy_next}:/etc/caddy/Caddyfile",
            "caddy:2", "caddy", "fmt", "--overwrite", "/etc/caddy/Caddyfile",
        ],
        capture_output=True,
        text=True,
    )

    # 6b. Validate candidate before replacing active file.
    validate = subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{caddy_next}:/etc/caddy/Caddyfile:ro",
            "caddy:2", "caddy", "validate", "--config", "/etc/caddy/Caddyfile",
        ],
        capture_output=True,
        text=True,
    )
    if validate.returncode != 0:
        raise RuntimeError(
            f"Caddyfile validation failed: {validate.stderr.strip()}"
        )

    # 7-8. Backup existing Caddyfile and promote candidate.
    caddyfile = caddy_dir / "Caddyfile"
    if caddyfile.exists():
        shutil.copy2(caddyfile, caddy_dir / "Caddyfile.bak")
    shutil.move(str(caddy_next), str(caddyfile))

    # 9. Render docker-compose.yml.
    render_file(
        repo / "templates" / "docker" / "caddy" / "docker-compose.yml.tmpl",
        caddy_dir / "docker-compose.yml",
        state,
    )

    # 10-12. Start or recreate container so the new Caddyfile is always applied.
    # --force-recreate ensures the container restarts even if the compose file
    # didn't change, which is required when the previous Caddyfile had admin off
    # (making hot-reload via the admin API impossible).
    up = subprocess.run(
        ["docker", "compose", "up", "-d", "--force-recreate"],
        cwd=str(caddy_dir),
        capture_output=True,
        text=True,
    )
    if up.returncode != 0:
        bak = caddy_dir / "Caddyfile.bak"
        if bak.exists():
            shutil.copy2(bak, caddyfile)
        raise RuntimeError(f"docker compose up failed: {up.stderr.strip()}. Restored previous Caddyfile.")

    log_path.write_text("caddy step completed\n")


def verify(state: State) -> VerificationResult:
    docker_net = state.get("docker_net", "caddy_net")

    # Container running?
    ps = subprocess.run(
        ["docker", "ps", "--filter", "name=^caddy$", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    if "caddy" not in ps.stdout:
        return VerificationResult.failure("caddy", "Caddy container is not running")

    # Network exists?
    net = subprocess.run(
        ["docker", "network", "inspect", docker_net],
        capture_output=True,
        text=True,
    )
    if net.returncode != 0:
        return VerificationResult.failure(
            "caddy", f"Docker network {docker_net} does not exist"
        )

    # Health endpoint responds?
    health = subprocess.run(
        ["curl", "-s", "http://localhost/health"],
        capture_output=True,
        text=True,
    )
    if health.returncode != 0 or "OK" not in health.stdout:
        return VerificationResult.failure("caddy", "Caddy health check failed")

    return VerificationResult.success("caddy", "Caddy is running and healthy")
