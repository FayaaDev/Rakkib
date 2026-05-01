"""Registry-driven service hooks used by Step 5."""

from __future__ import annotations

import json
import os
import pwd
import shutil
import subprocess
from pathlib import Path

from rich.console import Console

from rakkib.docker import container_running
from rakkib.doctor import wait_for_apt_locks
from rakkib.render import render_file
from rakkib.steps import selected_service_defs
from rakkib.tui import progress_spinner, progress_wait


console = Console()

_KUMA_MANAGED_PREFIX = "Managed by Rakkib (service: "
_OPENCLAW_INSTALL_URL = "https://openclaw.ai/install.sh"
_OPENCLAW_COMMAND_TIMEOUT = 900
_OPENCLAW_GATEWAY_TIMEOUT = 180
_OPENCLAW_PAIRING_TIMEOUT = 180
_OPENCLAW_GATEWAY_BIND = "lan"


def _write_text_if_changed(path: Path, content: str) -> bool:
    existing = path.read_text() if path.exists() else None
    if existing == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True


def _restart_service(data_root: Path, svc_id: str) -> None:
    svc_dir = data_root / "docker" / svc_id
    compose_path = svc_dir / "docker-compose.yml"
    if not compose_path.exists() or not container_running(svc_id):
        return
    subprocess.run(
        ["docker", "compose", "--project-directory", str(svc_dir), "restart"],
        check=True,
        capture_output=True,
        text=True,
    )


def _service_admin_user(state) -> tuple[str, Path, int]:
    admin_user = state.get("admin_user") or os.environ.get("SUDO_USER") or os.environ.get("USER")
    if not admin_user:
        raise RuntimeError("OpenClaw setup requires an admin_user in state or a real shell user in the environment.")

    record = pwd.getpwnam(str(admin_user))
    return str(admin_user), Path(record.pw_dir), int(record.pw_uid)


def _run_as_user(
    username: str,
    home_dir: Path,
    user_uid: int,
    command: list[str],
    *,
    check: bool = True,
    timeout: int | None = None,
    extra_env: dict[str, str] | None = None,
    timeout_label: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home_dir),
            "USER": username,
            "LOGNAME": username,
            "XDG_RUNTIME_DIR": f"/run/user/{user_uid}",
            "DBUS_SESSION_BUS_ADDRESS": f"unix:path=/run/user/{user_uid}/bus",
        }
    )
    if extra_env:
        env.update(extra_env)

    run_cmd = command
    if os.geteuid() == 0 and os.environ.get("USER") != username:
        run_cmd = [
            "sudo",
            "-n",
            "-u",
            username,
            "-H",
            "env",
            f"HOME={home_dir}",
            f"USER={username}",
            f"LOGNAME={username}",
            f"XDG_RUNTIME_DIR=/run/user/{user_uid}",
            f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{user_uid}/bus",
        ]
        if extra_env:
            run_cmd.extend(f"{key}={value}" for key, value in extra_env.items())
        run_cmd += command

    try:
        return subprocess.run(
            run_cmd, capture_output=True, text=True, check=check, env=env,
            timeout=timeout, stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        label = timeout_label or " ".join(command)
        raise RuntimeError(
            f"{label} timed out after {timeout} seconds. "
            "If Ubuntu unattended-upgrades or another package manager is still running, wait for it to finish and rerun `rakkib add openclaw`."
        ) from exc


def _run_as_service_user(
    state,
    command: list[str],
    *,
    check: bool = True,
    timeout: int | None = None,
    extra_env: dict[str, str] | None = None,
    timeout_label: str | None = None,
) -> subprocess.CompletedProcess[str]:
    admin_user, home_dir, user_uid = _service_admin_user(state)
    return _run_as_user(
        admin_user,
        home_dir,
        user_uid,
        command,
        check=check,
        timeout=timeout,
        extra_env=extra_env,
        timeout_label=timeout_label,
    )


def _root_user() -> tuple[str, Path, int]:
    record = pwd.getpwnam("root")
    return "root", Path(record.pw_dir), int(record.pw_uid)


def _resolve_openclaw_bin_for_user(state, username: str) -> Path | None:
    direct = shutil.which("openclaw") if os.environ.get("USER") == username else None
    if direct:
        return Path(direct).resolve()

    if username == "root":
        _, home_dir, user_uid = _root_user()
        result = _run_as_user("root", home_dir, user_uid, ["bash", "-lc", "command -v openclaw"], check=False)
    else:
        result = _run_as_service_user(state, ["bash", "-lc", "command -v openclaw"], check=False)
    if result.returncode != 0:
        return None

    resolved = result.stdout.strip()
    return Path(resolved).resolve() if resolved else None


def _resolve_openclaw_bin(state) -> Path | None:
    admin_user, _, _ = _service_admin_user(state)
    return _resolve_openclaw_bin_for_user(state, admin_user)


def _run_openclaw(state, openclaw_bin: Path, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run_as_service_user(
        state,
        [str(openclaw_bin), *args],
        check=check,
        timeout=_OPENCLAW_COMMAND_TIMEOUT,
        timeout_label=f"OpenClaw command `{openclaw_bin} {' '.join(args)}`",
    )


def _openclaw_output(result: subprocess.CompletedProcess[str]) -> str:
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    parts = [f"exit code: {result.returncode}"]
    if stdout:
        parts.append(f"stdout: {stdout}")
    if stderr:
        parts.append(f"stderr: {stderr}")
    return " | ".join(parts)


def _openclaw_paths(home_dir: Path) -> tuple[Path, Path]:
    return (
        home_dir / ".openclaw" / "openclaw.json",
        home_dir / ".config" / "systemd" / "user" / "openclaw-gateway.service",
    )


def _openclaw_dashboard_url(state) -> str | None:
    """Return the public dashboard URL with token pre-filled, or None if unavailable."""
    _, home_dir, _ = _service_admin_user(state)
    config_path, _ = _openclaw_paths(home_dir)
    try:
        config = json.loads(config_path.read_text())
        token = config.get("gateway", {}).get("auth", {}).get("token")
    except Exception:
        return None
    if not token or not isinstance(token, str):
        return None
    domain = str(state.get("domain") or "").strip()
    subdomain = str(state.get("subdomains.openclaw") or state.get("OPENCLAW_SUBDOMAIN") or "claw").strip()
    base = f"https://{subdomain}.{domain}" if domain and subdomain else "http://127.0.0.1:18789"
    return f"{base}/?token={token}"


def _openclaw_wait_for_pairing(state, openclaw_bin: Path) -> None:
    """If no devices are paired yet, prompt the user and auto-approve the first pairing request."""
    list_result = _run_openclaw(state, openclaw_bin, ["devices", "list", "--json"], check=False)
    if list_result.returncode != 0:
        return
    try:
        devices = json.loads(list_result.stdout)
    except Exception:
        return

    if devices.get("paired"):
        return  # Already has paired devices — nothing to do.

    console.print(
        "  [bold]OpenClaw:[/bold] Open the dashboard and click [bold]Connect[/bold] to pair your device."
        f" Waiting up to {_OPENCLAW_PAIRING_TIMEOUT}s..."
    )
    def poll_pairing() -> bool:
        list_result = _run_openclaw(state, openclaw_bin, ["devices", "list", "--json"], check=False)
        if list_result.returncode != 0:
            return False
        try:
            devices = json.loads(list_result.stdout)
        except Exception:
            return False

        if devices.get("paired"):
            # Approved via another path before we could catch the pending state.
            console.print("[green]  OpenClaw: device paired.[/green]")
            return True

        if devices.get("pending"):
            approve = _run_openclaw(state, openclaw_bin, ["devices", "approve", "--latest"], check=False)
            if approve.returncode == 0:
                console.print("[green]  OpenClaw: device paired and approved automatically.[/green]")
            else:
                console.print(
                    f"[yellow]  OpenClaw: pairing request found but auto-approve failed "
                    f"({_openclaw_output(approve)}). Run `openclaw devices approve --latest` manually.[/yellow]"
                )
            return True

        return False

    if progress_wait("Waiting for OpenClaw device pairing...", _OPENCLAW_PAIRING_TIMEOUT, poll_pairing, interval=3):
        return

    console.print(
        "[dim]  OpenClaw: no pairing request received within the timeout. "
        "Open the dashboard and click Connect, then run `openclaw devices approve --latest` on the server.[/dim]"
    )


def _wait_for_openclaw_package_locks() -> None:
    if shutil.which("apt-get") is None:
        return

    with progress_spinner("Waiting for apt/dpkg locks to clear..."):
        lock_error = wait_for_apt_locks()
    if lock_error:
        raise RuntimeError(f"OpenClaw setup cannot continue while apt/dpkg is locked. {lock_error}")


def _openclaw_gateway_healthcheck(timeout: int = _OPENCLAW_GATEWAY_TIMEOUT) -> bool:
    def poll() -> bool:
        result = subprocess.run(
            ["curl", "-fsS", "http://127.0.0.1:18789/healthz", "-o", "/dev/null"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    return progress_wait("Waiting for OpenClaw gateway health...", timeout, poll, interval=2)


def _migrate_root_openclaw_service(state) -> None:
    admin_user, _, _ = _service_admin_user(state)
    if admin_user == "root":
        return

    root_service = Path("/root/.config/systemd/user/openclaw-gateway.service")
    root_config = Path("/root/.openclaw/openclaw.json")
    if not root_service.exists() and not root_config.exists():
        return

    root_bin = _resolve_openclaw_bin_for_user(state, "root")
    if root_bin is None:
        return

    root_stop = _run_as_user("root", Path("/root"), 0, [str(root_bin), "gateway", "stop"], check=False)
    root_uninstall = _run_as_user("root", Path("/root"), 0, [str(root_bin), "gateway", "uninstall"], check=False)
    if root_uninstall.returncode == 0:
        return

    output = f"{root_stop.stdout}\n{root_stop.stderr}\n{root_uninstall.stdout}\n{root_uninstall.stderr}".lower()
    if "not installed" in output or "not found" in output:
        return
    raise RuntimeError(
        "Root-owned OpenClaw gateway cleanup failed before migrating to the admin user. "
        f"Command output: {root_uninstall.stdout.strip() or root_uninstall.stderr.strip() or root_stop.stdout.strip() or root_stop.stderr.strip()}"
    )


def _ensure_openclaw_gateway_bind(state, openclaw_bin: Path) -> None:
    bind = _run_openclaw(state, openclaw_bin, ["config", "set", "gateway.bind", _OPENCLAW_GATEWAY_BIND], check=False)
    if bind.returncode != 0:
        raise RuntimeError(
            "OpenClaw gateway bind update failed. "
            f"Command output: {bind.stdout.strip() or bind.stderr.strip()}"
        )


def _openclaw_allowed_origins(state) -> list[str]:
    origins = ["http://127.0.0.1:18789", "http://localhost:18789"]
    domain = str(state.get("domain") or "").strip()
    subdomain = str(state.get("subdomains.openclaw") or state.get("OPENCLAW_SUBDOMAIN") or "claw").strip()
    if domain and subdomain:
        origins.insert(0, f"https://{subdomain}.{domain}")
        origins.insert(1, f"http://{subdomain}.{domain}")
    return origins


def _ensure_openclaw_control_ui_allowed_origins(state, openclaw_bin: Path) -> None:
    origins = json.dumps(_openclaw_allowed_origins(state))
    result = _run_openclaw(
        state,
        openclaw_bin,
        ["config", "set", "gateway.controlUi.allowedOrigins", origins],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "OpenClaw Control UI allowedOrigins update failed. "
            f"Command output: {result.stdout.strip() or result.stderr.strip()}"
        )


def _homepage_services_content(state, registry: dict) -> str:
    groups: dict[str, list[str]] = {}
    for selected_svc in selected_service_defs(state, registry):
        homepage = selected_svc.get("homepage") or {}
        if not homepage:
            continue

        subdomain = state.get(f"subdomains.{selected_svc['id']}", selected_svc["id"])
        href = f"https://{subdomain}.{state.get('domain', 'localhost')}"
        block = (
            f"    - {homepage['name']}:\n"
            f"        href: {href}\n"
            f"        description: {homepage['description']}\n"
            f"        icon: {homepage['icon']}"
        )
        groups.setdefault(homepage["category"], []).append(block)

    lines = ["# Generated by Rakkib — edit manually or re-run Rakkib to regenerate."]
    for category in sorted(groups):
        lines.append(f"- {category}:")
        lines.extend(groups[category])
    return "\n".join(lines) + "\n"


def _resolve_monitoring_target(state, svc: dict, monitoring: dict) -> dict[str, object]:
    target = monitoring.get("target", "public_url")
    monitor_type = monitoring.get("type", "http")
    path = monitoring.get("path", "/")
    domain = state.get("domain", "localhost")
    subdomain = state.get(f"subdomains.{svc['id']}", svc["id"])
    hostname = f"{subdomain}.{domain}"

    if target == "public_url":
        if monitor_type == "ping":
            return {"hostname": hostname}
        if monitor_type == "tcp":
            return {"hostname": hostname, "port": int(monitoring.get("port", 443))}
        normalized_path = path if str(path).startswith("/") else f"/{path}"
        return {"url": f"https://{hostname}{normalized_path}"}

    if target == "host_port":
        port = monitoring.get("port") or svc.get("default_port")
        if port is None:
            raise ValueError(f"Service {svc['id']} monitoring.host_port requires a port")
        if monitor_type == "tcp":
            return {"hostname": "127.0.0.1", "port": int(port)}
        normalized_path = path if str(path).startswith("/") else f"/{path}"
        scheme = "https" if monitor_type == "https" else "http"
        return {"url": f"{scheme}://127.0.0.1:{int(port)}{normalized_path}"}

    if target == "container":
        port = monitoring.get("port") or svc.get("default_port")
        container_name = svc.get("container_name", svc["id"])
        if monitor_type == "ping":
            return {"hostname": container_name}
        if monitor_type == "tcp":
            if port is None:
                raise ValueError(f"Service {svc['id']} monitoring.container requires a port")
            return {"hostname": container_name, "port": int(port)}
        if port is None:
            raise ValueError(f"Service {svc['id']} monitoring.container requires a port")
        normalized_path = path if str(path).startswith("/") else f"/{path}"
        scheme = "https" if monitor_type == "https" else "http"
        return {"url": f"{scheme}://{container_name}:{int(port)}{normalized_path}"}

    if target == "custom":
        custom_url = monitoring.get("custom_url")
        if not custom_url:
            raise ValueError(f"Service {svc['id']} monitoring.custom requires custom_url")
        if monitor_type in {"ping", "tcp"}:
            host = monitoring.get("hostname")
            port = monitoring.get("port")
            if monitor_type == "ping" and host:
                return {"hostname": host}
            if monitor_type == "tcp" and host and port is not None:
                return {"hostname": host, "port": int(port)}
        return {"url": str(custom_url)}

    raise ValueError(f"Unknown monitoring target '{target}' for service {svc['id']}")


def _kuma_monitor_spec(state, svc: dict) -> dict[str, object] | None:
    monitoring = svc.get("monitoring") or {}
    if not monitoring.get("enabled"):
        return None

    spec: dict[str, object] = {
        "service_id": svc["id"],
        "name": monitoring.get("name") or (svc.get("homepage") or {}).get("name") or svc["id"],
        "type": monitoring.get("type", "http"),
        "interval": int(monitoring.get("interval", 60)),
        "timeout": int(monitoring.get("timeout", 10)),
        "maxretries": int(monitoring.get("retries", 3)),
    }
    spec.update(_resolve_monitoring_target(state, svc, monitoring))
    return spec


def _uptime_kuma_sync_payload(state, registry: dict) -> dict[str, object]:
    monitors = []
    for svc in selected_service_defs(state, registry):
        spec = _kuma_monitor_spec(state, svc)
        if spec is not None:
            monitors.append(spec)

    return {
        "admin": {
            "username": state.get("UPTIME_KUMA_ADMIN_USER", "admin"),
            "password": state.get("UPTIME_KUMA_ADMIN_PASS"),
        },
        "managed_prefix": _KUMA_MANAGED_PREFIX,
        "monitors": monitors,
    }


def homepage_services_yaml(
    state,
    svc: dict,
    repo: Path,
    data_root: Path,
    log_path: Path,
    registry: dict,
) -> None:
    """Generate Homepage services.yaml from registry homepage metadata."""
    del svc, repo, log_path
    config_dir = data_root / "data" / "homepage" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    _write_text_if_changed(config_dir / "services.yaml", _homepage_services_content(state, registry))


def _service_postgres_credentials(state, svc: dict) -> tuple[str, str, str]:
    postgres = svc.get("postgres") or {}
    role = postgres.get("role", svc["id"])
    db_name = postgres.get("db", role)
    password_key = postgres.get("password_key")
    if not password_key:
        raise RuntimeError(
            f"postgres login pre-flight is configured for service '{svc['id']}' without a password_key"
        )

    password = state.get(f"secrets.values.{password_key}")
    if password is None:
        password = state.get(password_key)
    if not password:
        raise RuntimeError(
            f"postgres login pre-flight failed for service '{svc['id']}': missing database password "
            f"'{password_key}' in state. Re-run `rakkib pull` or sync services again so Step 4 can provision Postgres."
        )

    return role, db_name, str(password)


def sync_shared_artifacts(state, repo: Path, data_root: Path, registry: dict) -> None:
    """Regenerate shared artifacts that derive from the full selected service set."""
    selected_ids = {svc["id"] for svc in selected_service_defs(state, registry)}

    homepage_changed = False
    if "homepage" in selected_ids:
        config_dir = data_root / "data" / "homepage" / "config"
        homepage_changed = _write_text_if_changed(
            config_dir / "services.yaml",
            _homepage_services_content(state, registry),
        )

    if homepage_changed:
        _restart_service(data_root, "homepage")

    if "uptime-kuma" in selected_ids:
        kuma_data_dir = data_root / "data" / "uptime-kuma"
        kuma_data_dir.mkdir(parents=True, exist_ok=True)

        payload = json.dumps(_uptime_kuma_sync_payload(state, registry), indent=2, sort_keys=True) + "\n"
        _write_text_if_changed(kuma_data_dir / "rakkib-monitors.json", payload)

        sync_script = repo / "templates" / "docker" / "uptime-kuma" / "sync-monitors.cjs.tmpl"
        render_file(sync_script, kuma_data_dir / "sync-monitors.cjs", state)

        if container_running("uptime-kuma"):
            subprocess.run(
                ["docker", "exec", "uptime-kuma", "node", "/app/data/sync-monitors.cjs"],
                check=True,
                capture_output=True,
                text=True,
            )


def service_postgres_login_preflight(
    state,
    svc: dict,
    repo: Path,
    data_root: Path,
    log_path: Path,
    registry: dict,
) -> None:
    """Fail fast if a service cannot log into the shared postgres database."""
    del repo, data_root, log_path, registry
    role, db_name, password = _service_postgres_credentials(state, svc)

    result = subprocess.run(
        [
            "docker",
            "exec",
            "-e",
            f"PGPASSWORD={password}",
            "postgres",
            "psql",
            "-h",
            "127.0.0.1",
            "-U",
            role,
            "-d",
            db_name,
            "-c",
            "select 1;",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"postgres login pre-flight failed for service '{svc['id']}': the database login is not ready "
            "in the postgres container. Ensure Step 4 completed successfully and that the "
            "rendered service password matches the Postgres role password.\n"
            f"psql output: {result.stdout.strip() or result.stderr.strip()}"
        )


def openclaw_install(
    state,
    svc: dict,
    repo: Path,
    data_root: Path,
    log_path: Path,
    registry: dict,
) -> None:
    """Install OpenClaw and ensure a minimal local gateway is configured."""
    del svc, repo, data_root, registry

    if shutil.which("curl") is None:
        raise RuntimeError("OpenClaw setup requires curl. Install curl and re-run `rakkib pull`.")

    _wait_for_openclaw_package_locks()

    if os.geteuid() == 0:
        admin_user, _, _ = _service_admin_user(state)
        subprocess.run(["loginctl", "enable-linger", admin_user], capture_output=True, text=True, check=True)
        _migrate_root_openclaw_service(state)

    openclaw_bin = _resolve_openclaw_bin(state)
    if openclaw_bin is None:
        with progress_spinner("Installing OpenClaw CLI..."):
            install = _run_as_service_user(
                state,
                ["bash", "-lc", f"curl -fsSL {_OPENCLAW_INSTALL_URL} | bash -s -- --no-onboard --no-prompt"],
                check=False,
                timeout=_OPENCLAW_COMMAND_TIMEOUT,
                extra_env={"OPENCLAW_NO_PROMPT": "1"},
                timeout_label="OpenClaw installer",
            )
        if install.returncode != 0:
            raise RuntimeError(
                "OpenClaw installation failed. "
                f"Command output: {_openclaw_output(install)}"
            )
        openclaw_bin = _resolve_openclaw_bin(state)
        if openclaw_bin is None:
            raise RuntimeError(
                "OpenClaw installation completed but the `openclaw` CLI is still unavailable on PATH. "
                "Check the target user's global npm/bin path, such as `$(npm prefix -g)/bin`, and re-run `rakkib pull`."
            )

    version = _run_openclaw(state, openclaw_bin, ["--version"], check=False)
    if version.returncode != 0:
        raise RuntimeError(
            "OpenClaw CLI was found but `openclaw --version` failed. "
            f"Command output: {_openclaw_output(version)}"
        )

    _, home_dir, _ = _service_admin_user(state)
    config_path, service_path = _openclaw_paths(home_dir)
    if config_path.exists():
        console.print("[dim]  openclaw: already onboarded, updating config...[/dim]")
        _ensure_openclaw_gateway_bind(state, openclaw_bin)
        _ensure_openclaw_control_ui_allowed_origins(state, openclaw_bin)
        return

    with progress_spinner("Running OpenClaw onboarding..."):
        onboard = _run_openclaw(
            state,
            openclaw_bin,
            [
                "onboard",
                "--non-interactive",
                "--mode",
                "local",
                "--auth-choice",
                "skip",
                "--gateway-port",
                "18789",
                "--gateway-bind",
                _OPENCLAW_GATEWAY_BIND,
                "--install-daemon",
                "--skip-bootstrap",
                "--skip-skills",
                "--accept-risk",
            ],
            check=False,
        )
    if onboard.returncode != 0:
        if not (config_path.exists() and service_path.exists()):
            raise RuntimeError(
                "OpenClaw onboarding failed. "
                f"Command output: {_openclaw_output(onboard)}"
            )

    _ensure_openclaw_gateway_bind(state, openclaw_bin)
    _ensure_openclaw_control_ui_allowed_origins(state, openclaw_bin)


def openclaw_gateway_restart(
    state,
    svc: dict,
    repo: Path,
    data_root: Path,
    log_path: Path,
    registry: dict,
) -> None:
    """Ensure the OpenClaw gateway daemon is installed, running, and healthy."""
    del svc, repo, data_root, registry

    openclaw_bin = _resolve_openclaw_bin(state)
    if openclaw_bin is None:
        raise RuntimeError("OpenClaw gateway restart requested but the `openclaw` CLI is not installed for the admin user.")

    with progress_spinner("Installing OpenClaw gateway service..."):
        install = _run_openclaw(state, openclaw_bin, ["gateway", "install", "--force"], check=False)
    if install.returncode != 0:
        raise RuntimeError(
            "OpenClaw gateway install failed. "
            f"Command output: {_openclaw_output(install)}"
        )

    with progress_spinner("Restarting OpenClaw gateway..."):
        restart = _run_openclaw(state, openclaw_bin, ["gateway", "restart"], check=False)
    if restart.returncode != 0:
        raise RuntimeError(
            "OpenClaw gateway restart failed. "
            f"Command output: {_openclaw_output(restart)}"
        )

    if not _openclaw_gateway_healthcheck():
        status = _run_openclaw(state, openclaw_bin, ["gateway", "status", "--require-rpc"], check=False)
        raise RuntimeError(
            "OpenClaw gateway did not become healthy on 127.0.0.1:18789/healthz. "
            f"Status output: {_openclaw_output(status)}"
        )

    url = _openclaw_dashboard_url(state)
    if url:
        console.print(f"[green]  OpenClaw ready:[/green] {url}")

    _openclaw_wait_for_pairing(state, openclaw_bin)


def openclaw_gateway_uninstall(
    state,
    svc: dict,
    repo: Path,
    data_root: Path,
    log_path: Path,
    registry: dict,
) -> None:
    """Purge the managed OpenClaw gateway service while preserving user state."""
    del svc, repo, data_root, log_path, registry

    openclaw_bin = _resolve_openclaw_bin(state)
    if openclaw_bin is None:
        return

    uninstall = _run_openclaw(state, openclaw_bin, ["gateway", "uninstall"], check=False)
    if uninstall.returncode == 0:
        return

    output = f"{uninstall.stdout}\n{uninstall.stderr}".lower()
    if "not installed" in output or "not found" in output:
        return
    raise RuntimeError(
        "OpenClaw gateway uninstall failed. "
        f"Command output: {uninstall.stdout.strip() or uninstall.stderr.strip()}"
    )


POST_RENDER_HOOKS = {
    "homepage_services_yaml": homepage_services_yaml,
}

PRE_START_HOOKS = {
    "service_postgres_login_preflight": service_postgres_login_preflight,
    "openclaw_install": openclaw_install,
}

POST_START_HOOKS = {
    "openclaw_gateway_restart": openclaw_gateway_restart,
}

RESTART_HOOKS = {
    "openclaw_gateway_restart": openclaw_gateway_restart,
}

REMOVE_HOOKS = {
    "openclaw_gateway_uninstall": openclaw_gateway_uninstall,
}
