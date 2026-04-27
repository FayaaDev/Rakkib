"""Step 40 — Cloudflare.

Render and deploy the Cloudflare tunnel after the user confirms the setup.
"""

from __future__ import annotations

import getpass
import json
import os
import shutil
import subprocess
from pathlib import Path

from rakkib.docker import compose_up, container_running, DockerError
from rakkib.render import render_file
from rakkib.state import State
from rakkib.steps import VerificationResult


def _repo_dir() -> Path:
    """Return the package data directory (contains ``templates/``)."""
    return Path(__file__).resolve().parent.parent / "data"


def _cloudflared_bin() -> str:
    """Return the path to the cloudflared binary."""
    local_bin = Path.home() / ".local" / "bin" / "cloudflared"
    if local_bin.exists():
        return str(local_bin)
    return "cloudflared"


def _ensure_cloudflared() -> None:
    """Download and install cloudflared via wget + apt if not found."""
    deb_path = Path("/tmp/cloudflared-linux-amd64.deb")
    _run(["wget", "-q", "-O", str(deb_path),
          "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"])
    _run(["sudo", "apt", "install", "-y", str(deb_path)])
    deb_path.unlink(missing_ok=True)


def _run(
    cmd: list[str],
    env: dict[str, str] | None = None,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command with optional env override."""
    merged_env = {**os.environ}
    if env:
        merged_env.update(env)

    result = subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        env=merged_env,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n"
            f"stderr: {result.stderr.strip() if result.stderr else ''}"
        )
    return result


def _get_tunnel_uuid(tunnel_name: str, env: dict[str, str] | None = None) -> str | None:
    """Look up tunnel UUID by name. Returns None if not found."""
    result = _run(
        [_cloudflared_bin(), "tunnel", "list", "--output", "json"],
        env=env,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        tunnels = json.loads(result.stdout)
        for t in tunnels:
            if t.get("name") == tunnel_name:
                return t.get("id")
    except json.JSONDecodeError:
        pass
    return None


def run(state: State) -> None:
    data_root = Path(state.get("data_root", "/srv"))
    auth_method = state.get("cloudflare.auth_method")
    tunnel_strategy = state.get("cloudflare.tunnel_strategy")
    tunnel_name = state.get("cloudflare.tunnel_name")
    ssh_subdomain = state.get("cloudflare.ssh_subdomain", "ssh")
    domain = state.get("domain")
    docker_net = state.get("docker_net", "caddy_net")
    lan_ip = state.get("lan_ip", "127.0.0.1")
    metrics_port = state.get("cloudflared_metrics_port", "20241")
    admin_user = state.get("admin_user")
    zone_in_cloudflare = state.get("cloudflare.zone_in_cloudflare", False)

    cloudflared_dir = data_root / "data" / "cloudflared"
    docker_dir = data_root / "docker" / "cloudflared"
    log_path = data_root / "logs" / "cloudflare.log"

    cloudflared_dir.mkdir(parents=True, exist_ok=True)
    docker_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 0. Stop if zone is not in Cloudflare
    if not zone_in_cloudflare:
        raise RuntimeError(
            "The domain is not active in Cloudflare. "
            "Complete Cloudflare zone setup first, then resume."
        )

    # 1. Confirm cloudflared CLI is installed
    try:
        _run([_cloudflared_bin(), "--version"])
    except RuntimeError:
        print("cloudflared not found, installing via wget + apt...")
        _ensure_cloudflared()

    cert_path = cloudflared_dir / "cert.pem"
    default_cert = Path.home() / ".cloudflared" / "cert.pem"
    token_env: dict[str, str] | None = None

    # 4-5. Handle auth methods
    if auth_method == "browser_login":
        if not cert_path.exists():
            if default_cert.exists():
                shutil.copy2(default_cert, cert_path)
            else:
                headless = state.get("cloudflare.headless", False)
                if headless:
                    print(
                        "\nStep 40 is paused for Cloudflare approval.\n"
                        "cloudflared tunnel login will print a URL.\n"
                        "Open that URL on another signed-in device, approve the domain,\n"
                        "then return here.\n"
                    )
                else:
                    print(
                        "\nStep 40 is paused for Cloudflare approval.\n"
                        "A browser window will open for Cloudflare login.\n"
                        "Approve the domain, then return here.\n"
                    )

                result = subprocess.run(
                    [_cloudflared_bin(), "tunnel", "login"],
                    text=True,
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"cloudflared tunnel login failed: "
                        f"{result.stderr.strip() if result.stderr else 'unknown error'}"
                    )

                if default_cert.exists() and not cert_path.exists():
                    shutil.copy2(default_cert, cert_path)

        # Verify login succeeded
        list_result = _run(
            [_cloudflared_bin(), "tunnel", "list"],
            check=False,
        )
        if list_result.returncode != 0:
            raise RuntimeError(
                "cloudflared tunnel list failed after login. "
                "Resolve auth before continuing."
            )

    elif auth_method == "api_token":
        api_token = getpass.getpass("Cloudflare API token: ")
        if not api_token:
            raise RuntimeError("API token is required for api_token auth method.")

        verify_result = subprocess.run(
            [
                "curl", "-fsS", "--max-time", "10",
                "-H", f"Authorization: Bearer {api_token}",
                "https://api.cloudflare.com/client/v4/user/tokens/verify",
            ],
            capture_output=True,
            text=True,
        )
        if verify_result.returncode != 0:
            raise RuntimeError("Cloudflare API token verification failed.")

        token_env = {"CLOUDFLARE_API_TOKEN": api_token}

        list_result = _run(
            [_cloudflared_bin(), "tunnel", "list"],
            env=token_env,
            check=False,
        )
        if list_result.returncode != 0:
            raise RuntimeError(
                "cloudflared tunnel list failed with API token. "
                "Resolve auth before continuing."
            )

    elif auth_method == "existing_tunnel":
        tunnel_uuid = state.get("cloudflare.tunnel_uuid")
        creds_host_path = state.get("cloudflare.tunnel_creds_host_path")

        if not tunnel_uuid or not creds_host_path or not Path(creds_host_path).exists():
            # Need to repair auth
            if not cert_path.exists():
                if default_cert.exists():
                    shutil.copy2(default_cert, cert_path)
                else:
                    print(
                        "\nStep 40 needs Cloudflare login to repair missing credentials.\n"
                        "cloudflared tunnel login will be initiated.\n"
                    )
                    result = subprocess.run(
                        [_cloudflared_bin(), "tunnel", "login"],
                        text=True,
                    )
                    if result.returncode != 0:
                        raise RuntimeError(
                            f"cloudflared tunnel login failed: "
                            f"{result.stderr.strip() if result.stderr else 'unknown error'}"
                        )
                    if default_cert.exists() and not cert_path.exists():
                        shutil.copy2(default_cert, cert_path)

    # 7-9. Handle tunnel discovery / creation
    tunnel_uuid = state.get("cloudflare.tunnel_uuid")

    if tunnel_strategy == "new":
        existing_uuid = _get_tunnel_uuid(tunnel_name, env=token_env)
        if existing_uuid:
            tunnel_uuid = existing_uuid
        else:
            _run(
                [_cloudflared_bin(), "tunnel", "create", tunnel_name],
                env=token_env,
            )
            tunnel_uuid = _get_tunnel_uuid(tunnel_name, env=token_env)
            if not tunnel_uuid:
                raise RuntimeError(
                    f"Failed to get UUID for newly created tunnel '{tunnel_name}'"
                )

    elif tunnel_strategy == "existing":
        if not tunnel_uuid:
            existing_uuid = _get_tunnel_uuid(tunnel_name, env=token_env)
            if existing_uuid:
                tunnel_uuid = existing_uuid
            else:
                raise RuntimeError(
                    f"Existing tunnel '{tunnel_name}' not found. "
                    "Verify the tunnel name or create a new one."
                )

        info_result = _run(
            [_cloudflared_bin(), "tunnel", "info", tunnel_uuid],
            env=token_env,
            check=False,
        )
        if info_result.returncode != 0:
            raise RuntimeError(
                f"Tunnel info failed for UUID {tunnel_uuid}. "
                "The tunnel may not exist or auth may be invalid."
            )

    # 11. Ensure credentials JSON is at standardized host path
    creds_host_path = cloudflared_dir / f"{tunnel_uuid}.json"
    creds_container_path = f"/home/nonroot/.cloudflared/{tunnel_uuid}.json"

    if not creds_host_path.exists():
        default_creds = Path.home() / ".cloudflared" / f"{tunnel_uuid}.json"
        if default_creds.exists():
            shutil.copy2(default_creds, creds_host_path)
        else:
            raise RuntimeError(
                f"Tunnel credentials file not found at {creds_host_path} "
                f"or {default_creds}. Run cloudflared tunnel login and ensure "
                "the tunnel was created in the correct account."
            )

    # 12. Set file permissions on credentials JSON
    os.chmod(creds_host_path, 0o600)
    if admin_user:
        import pwd

        try:
            pw = pwd.getpwnam(admin_user)
            os.chown(creds_host_path, pw.pw_uid, pw.pw_gid)
        except KeyError:
            pass

    # 13. Update state with final values
    state.set("cloudflare.tunnel_uuid", tunnel_uuid)
    state.set("cloudflare.tunnel_creds_host_path", str(creds_host_path))
    state.set("cloudflare.tunnel_creds_container_path", creds_container_path)

    # Set top-level aliases so templates resolve {{TUNNEL_UUID}} etc.
    state.set("tunnel_uuid", tunnel_uuid)
    state.set("tunnel_creds_host_path", str(creds_host_path))
    state.set("tunnel_creds_container_path", creds_container_path)
    state.set("ssh_subdomain", ssh_subdomain)
    if not state.has("cloudflared_metrics_port"):
        state.set("cloudflared_metrics_port", metrics_port)

    state.save()

    # 14-15. Render templates
    repo = _repo_dir()
    render_file(
        repo / "templates" / "cloudflared" / "config.yml.tmpl",
        cloudflared_dir / "config.yml",
        state,
    )
    render_file(
        repo / "templates" / "docker" / "cloudflared" / "docker-compose.yml.tmpl",
        docker_dir / "docker-compose.yml",
        state,
    )

    # 16. Verify tunnel can be inspected before DNS changes
    _run(
        [_cloudflared_bin(), "tunnel", "info", tunnel_uuid],
        env=token_env,
    )

    # 17. Create or update DNS routes
    dns_routes = [domain, f"*.{domain}", f"{ssh_subdomain}.{domain}"]
    for route in dns_routes:
        route_result = _run(
            [_cloudflared_bin(), "tunnel", "route", "dns", tunnel_uuid, route],
            env=token_env,
            check=False,
        )
        if route_result.returncode != 0:
            # Fallback: try with tunnel_name
            route_result = _run(
                [_cloudflared_bin(), "tunnel", "route", "dns", tunnel_name, route],
                env=token_env,
                check=False,
            )
            if route_result.returncode != 0:
                raise RuntimeError(
                    f"DNS route creation failed for {route}: "
                    f"{route_result.stderr.strip() if route_result.stderr else 'unknown error'}"
                )

    # 19. Temporary API token was never persisted; token_env goes out of scope here.

    # 20. Start container (redirect output to log file)
    try:
        compose_up(docker_dir, log_path=log_path)
    except DockerError as exc:
        raise RuntimeError(
            f"docker compose up failed for cloudflared: {exc.stderr}"
        )

    log_path.write_text("cloudflare step completed\n")


def verify(state: State) -> VerificationResult:
    data_root = Path(state.get("data_root", "/srv"))
    auth_method = state.get("cloudflare.auth_method")
    tunnel_uuid = state.get("cloudflare.tunnel_uuid") or state.get("tunnel_uuid")
    tunnel_creds_host_path = (
        state.get("cloudflare.tunnel_creds_host_path")
        or state.get("tunnel_creds_host_path")
    )
    metrics_port = state.get("cloudflared_metrics_port", "20241")

    # cloudflared --version
    version = subprocess.run(
        [_cloudflared_bin(), "--version"],
        capture_output=True,
        text=True,
    )
    if version.returncode != 0:
        return VerificationResult.failure(
            "cloudflare",
            "cloudflared CLI is not installed or runnable",
        )

    # data dir exists
    cloudflared_dir = data_root / "data" / "cloudflared"
    if not cloudflared_dir.exists():
        return VerificationResult.failure(
            "cloudflare",
            f"Cloudflared data directory {cloudflared_dir} does not exist",
        )

    # cert.pem for browser_login
    if auth_method == "browser_login":
        cert_path = cloudflared_dir / "cert.pem"
        if not cert_path.exists():
            return VerificationResult.failure(
                "cloudflare",
                f"Browser login cert.pem not found at {cert_path}",
            )

    # cloudflared tunnel list
    list_result = subprocess.run(
        [_cloudflared_bin(), "tunnel", "list"],
        capture_output=True,
        text=True,
    )
    if list_result.returncode != 0:
        return VerificationResult.failure(
            "cloudflare",
            f"cloudflared tunnel list failed: {list_result.stderr.strip()}",
        )

    # cloudflared tunnel info
    if tunnel_uuid:
        info_result = subprocess.run(
            [_cloudflared_bin(), "tunnel", "info", tunnel_uuid],
            capture_output=True,
            text=True,
        )
        if info_result.returncode != 0:
            return VerificationResult.failure(
                "cloudflare",
                f"cloudflared tunnel info failed for {tunnel_uuid}: "
                f"{info_result.stderr.strip()}",
            )

    # config.yml exists
    config_path = cloudflared_dir / "config.yml"
    if not config_path.exists():
        return VerificationResult.failure(
            "cloudflare",
            f"config.yml not found at {config_path}",
        )

    # credentials JSON exists
    if tunnel_creds_host_path:
        if not Path(tunnel_creds_host_path).exists():
            return VerificationResult.failure(
                "cloudflare",
                f"Tunnel credentials not found at {tunnel_creds_host_path}",
            )

    # docker container running
    if not container_running("cloudflared"):
        return VerificationResult.failure(
            "cloudflare",
            "cloudflared container is not running",
        )

    # metrics endpoint responds
    health = subprocess.run(
        ["curl", "-fsS", f"http://127.0.0.1:{metrics_port}/metrics"],
        capture_output=True,
        text=True,
    )
    if health.returncode != 0:
        return VerificationResult.failure(
            "cloudflare",
            f"cloudflared metrics endpoint failed on port {metrics_port}",
        )

    return VerificationResult.success(
        "cloudflare", "Cloudflare tunnel is running and healthy"
    )
