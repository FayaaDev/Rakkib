"""Step 5 — Services.

Deploy foundation bundle services and selected optional services.
"""

from __future__ import annotations

import functools
import subprocess
from pathlib import Path
from typing import Callable

import yaml

from rakkib.docker import (
    compose_up,
    container_publishes_port,
    container_running,
)
from rakkib.hooks.services import POST_RENDER_HOOKS, POST_START_HOOKS, PRE_START_HOOKS
from rakkib.normalize import eval_when
from rakkib.render import render_file
from rakkib.secrets import FACTORIES
from rakkib.state import State
from rakkib.steps import VerificationResult, selected_service_defs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo_dir() -> Path:
    """Return the package data directory (contains ``templates/``)."""
    return Path(__file__).resolve().parent.parent / "data"


@functools.lru_cache(maxsize=1)
def _load_registry() -> dict:
    with (_repo_dir() / "registry.yaml").open() as fh:
        return yaml.safe_load(fh)


def _selected_and_always_services(state: State, registry: dict) -> list[dict]:
    always = [svc for svc in registry["services"] if svc.get("state_bucket") == "always" and svc.get("secrets")]
    return always + selected_service_defs(state, registry)


def _resolve_declared_value(spec: str | dict) -> str:
    if isinstance(spec, str):
        spec = {"factory": spec}

    if "value" in spec:
        return str(spec["value"])

    factory_name = spec.get("factory")
    if factory_name not in FACTORIES:
        raise ValueError(f"Unknown secret factory: {factory_name}")

    factory = FACTORIES[factory_name]
    kwargs = dict(spec.get("kwargs") or {})
    if "length" in spec:
        kwargs.setdefault("length", spec["length"])
    return factory(**kwargs)


def _condition_matches(condition: dict, state: State, selected_ids: set[str]) -> bool:
    required_services = condition.get("when_services", [])
    if any(service_id not in selected_ids for service_id in required_services):
        return False

    when = condition.get("when")
    if when and not eval_when(when, state):
        return False

    return True


def _generate_missing_secrets(state: State) -> None:
    """Generate secrets that are not yet present in state.

    Checks both the flat namespace and ``secrets.values`` (set by Step 4)
    so that passwords used in init-services.sql are reused in service .env
    files, avoiding divergence.
    """
    registry = _load_registry()
    services = _selected_and_always_services(state, registry)
    selected_ids = {svc["id"] for svc in selected_service_defs(state, registry)}
    secrets_values = dict(state.get("secrets.values", {}) or {})

    def _ensure(key: str, spec: str | dict) -> None:
        value = state.get(key)
        if value is None:
            value = secrets_values.get(key)
        if value is None:
            value = _resolve_declared_value(spec)
        state.set(key, value)
        secrets_values[key] = value

    for svc in services:
        for key, spec in (svc.get("secrets") or {}).items():
            _ensure(key, spec)

    for svc in services:
        for condition in svc.get("conditional_secrets", []):
            if not _condition_matches(condition, state, selected_ids):
                continue
            for key, spec in (condition.get("keys") or {}).items():
                _ensure(key, spec)

    if secrets_values:
        state.set("secrets.values", secrets_values)


# ---------------------------------------------------------------------------
# Per-service helpers
# ---------------------------------------------------------------------------


def _render_env_example(
    state: State,
    tmpl_path: Path,
    dst_path: Path,
    preserve_keys: list[str] | None = None,
) -> None:
    """Render an .env.example template to .env, preserving existing keys when requested."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # If destination exists and we have preserve keys, merge them into state
    # so the rendered output keeps existing values.
    if dst_path.exists() and preserve_keys:
        existing = _parse_dotenv(dst_path.read_text())
        for key in preserve_keys:
            if key in existing and existing[key]:
                state.set(key, existing[key])

    render_file(tmpl_path, dst_path, state)
    dst_path.chmod(0o600)


def _parse_dotenv(text: str) -> dict[str, str]:
    """Parse a simple KEY=VALUE env file."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip().strip("'\"")
    return result


def _render_caddy_route(state: State, svc: dict, repo: Path, data_root: Path) -> None:
    """Render the appropriate Caddy route template for a service."""
    svc_id = svc["id"]
    routes_dir = data_root / "docker" / "caddy" / "routes"
    routes_dir.mkdir(parents=True, exist_ok=True)

    foundation = set(state.get("foundation_services", []) or [])
    authentik_enabled = "authentik" in foundation

    caddy = svc.get("caddy") or {}
    tmpl_name = caddy.get("template")
    if not authentik_enabled and caddy.get("public_template"):
        tmpl_name = caddy["public_template"]

    if tmpl_name is None:
        return

    tmpl_path = repo / "templates" / "caddy" / "routes" / tmpl_name
    if tmpl_path.exists():
        render_file(tmpl_path, routes_dir / f"{svc_id}.caddy", state)


def _prepare_service_data(state: State, svc: dict, data_root: Path) -> None:
    for relative_dir in svc.get("data_dirs", []):
        (data_root / relative_dir).mkdir(parents=True, exist_ok=True)

    chown = svc.get("chown")
    if not chown or state.get("platform", "linux") != "linux":
        return

    service_data_root = data_root / "data" / svc["id"]
    if not service_data_root.exists():
        return

    subprocess.run(
        [
            "sudo",
            "-n",
            "chown",
            "-R",
            f"{chown['uid']}:{chown['gid']}",
            str(service_data_root),
        ],
        capture_output=True,
        text=True,
    )


def _render_extra_templates(state: State, svc: dict, repo: Path, data_root: Path) -> None:
    for extra in svc.get("extra_templates", []):
        src = repo / extra["src"]
        dst = data_root / extra["dst"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        render_file(src, dst, state)


def _run_named_hooks(
    hook_names: list[str],
    hook_registry: dict[str, Callable],
    state: State,
    svc: dict,
    repo: Path,
    data_root: Path,
    log_path: Path,
    registry: dict,
) -> None:
    for hook_name in hook_names:
        hook = hook_registry.get(hook_name)
        if hook is None:
            raise ValueError(f"Unknown service hook: {hook_name}")
        hook(state, svc, repo, data_root, log_path, registry)


def _reload_caddy(data_root: Path) -> None:
    caddy_dir = data_root / "docker" / "caddy"
    caddyfile = caddy_dir / "Caddyfile"

    # Format the Caddyfile by running caddy fmt inside the container and
    # writing the result to the host-side file (the bind mount is read-only
    # inside the container, so --overwrite cannot work).
    fmt_result = subprocess.run(
        ["docker", "compose", "exec", "caddy", "caddy", "fmt", "/etc/caddy/Caddyfile"],
        cwd=str(caddy_dir),
        capture_output=True,
        text=True,
    )
    if fmt_result.returncode == 0 and fmt_result.stdout.strip():
        caddyfile.write_text(fmt_result.stdout)

    # The Caddyfile has `admin off` so `caddy reload` (which needs the admin
    # API) will always fail. Restart the container instead.
    subprocess.run(
        ["docker", "compose", "restart", "caddy"],
        cwd=str(caddy_dir),
        capture_output=True,
        text=True,
        check=True,
    )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def _deploy_single_service(state: State, svc: dict, repo: Path, data_root: Path) -> None:
    """Render templates, create dirs, and start a single service."""
    if svc.get("host_service"):
        return

    svc_id = svc["id"]
    svc_dir = data_root / "docker" / svc_id
    log_path = data_root / "logs" / f"step5-{svc_id}.log"
    registry = _load_registry()
    hooks = svc.get("hooks") or {}

    _prepare_service_data(state, svc, data_root)

    # --- Render templates ------------------------------------------------

    # .env.example -> .env
    env_tmpl = repo / "templates" / "docker" / svc_id / ".env.example"
    env_path = svc_dir / ".env"
    if env_tmpl.exists():
        preserve = svc.get("env_preserve_keys", [])
        _render_env_example(state, env_tmpl, env_path, preserve)

    # docker-compose.yml
    compose_tmpl = repo / "templates" / "docker" / svc_id / "docker-compose.yml.tmpl"
    if compose_tmpl.exists():
        render_file(compose_tmpl, svc_dir / "docker-compose.yml", state)

    _render_extra_templates(state, svc, repo, data_root)
    _run_named_hooks(hooks.get("post_render", []), POST_RENDER_HOOKS, state, svc, repo, data_root, log_path, registry)

    _run_named_hooks(hooks.get("pre_start", []), PRE_START_HOOKS, state, svc, repo, data_root, log_path, registry)

    # --- Start service ---------------------------------------------------
    compose_up(svc_dir, log_path=log_path)

    _run_named_hooks(hooks.get("post_start", []), POST_START_HOOKS, state, svc, repo, data_root, log_path, registry)

    # --- Caddy route -----------------------------------------------------
    _render_caddy_route(state, svc, repo, data_root)


def run(state: State) -> None:
    repo = _repo_dir()
    data_root = Path(state.get("data_root", "/srv"))
    registry = _load_registry()

    _generate_missing_secrets(state)
    services = selected_service_defs(state, registry)

    for svc in services:
        _deploy_single_service(state, svc, repo, data_root)

    # --- Reload Caddy after all services -------------------------------------
    _reload_caddy(data_root)


def run_single_service(state: State, svc_id: str) -> None:
    """Deploy a single service by ID."""
    repo = _repo_dir()
    data_root = Path(state.get("data_root", "/srv"))
    registry = _load_registry()

    by_id = {s["id"]: s for s in registry["services"]}
    if svc_id not in by_id:
        raise ValueError(f"Service {svc_id} not found in registry")

    _generate_missing_secrets(state)
    svc = by_id[svc_id]
    _deploy_single_service(state, svc, repo, data_root)
    _reload_caddy(data_root)


# ---------------------------------------------------------------------------
# Restart
# ---------------------------------------------------------------------------


def restart_service(state: State, svc_id: str) -> None:
    """Restart a single service by running docker compose restart in its directory."""
    data_root = Path(state.get("data_root", "/srv"))
    svc_dir = data_root / "docker" / svc_id
    if not (svc_dir / "docker-compose.yml").exists():
        raise ValueError(f"No docker-compose.yml found for service '{svc_id}' at {svc_dir}")
    subprocess.run(
        ["docker", "compose", "--project-directory", str(svc_dir), "restart"],
        check=True,
    )


def restart_all(state: State) -> list[str]:
    """Restart all deployed services in dependency order. Returns ids of restarted services.

    Order: postgres → cloudflared → foundation/selected (dependency order) → caddy
    Caddy is always last so routes are live after all services are up.
    """
    data_root = Path(state.get("data_root", "/srv"))
    registry = _load_registry()

    always_ids = [
        s["id"]
        for s in registry["services"]
        if s.get("state_bucket") == "always" and s["id"] != "caddy"
    ]
    selected = selected_service_defs(state, registry)
    selected_ids = [s["id"] for s in selected]

    order = []
    for svc_id in always_ids:
        if svc_id not in order:
            order.append(svc_id)
    for svc_id in selected_ids:
        if svc_id not in order:
            order.append(svc_id)
    order.append("caddy")

    restarted: list[str] = []
    for svc_id in order:
        svc_dir = data_root / "docker" / svc_id
        if not (svc_dir / "docker-compose.yml").exists():
            continue
        subprocess.run(
            ["docker", "compose", "--project-directory", str(svc_dir), "restart"],
            check=True,
        )
        restarted.append(svc_id)

    return restarted


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def verify(state: State) -> VerificationResult:
    registry = _load_registry()
    services = selected_service_defs(state, registry)

    for svc in services:
        if svc.get("host_service"):
            continue

        svc_id = svc["id"]
        port = svc.get("default_port")

        # Determine expected container name
        container_name = svc.get("container_name", svc_id)

        if not container_running(container_name):
            return VerificationResult.failure(
                "services",
                f"Container {container_name} ({svc_id}) is not running",
            )

        needs_host_port = svc.get("host_port", False)
        if port and needs_host_port and not container_publishes_port(container_name, port):
            return VerificationResult.failure(
                "services",
                f"Container {container_name} does not publish port {port}",
            )

    return VerificationResult.success("services", "All selected services are running")
