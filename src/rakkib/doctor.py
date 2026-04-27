"""Host preflight checks.

Each check returns a CheckResult with name, status, blocking flag, and message.
"""

from __future__ import annotations

import json
import platform
import shutil
import struct
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from rakkib.state import State


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""

    name: str
    status: str  # "ok", "warn", "fail"
    blocking: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _command_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _normalize_arch(raw: str) -> str | None:
    mapping = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    return mapping.get(raw)


def _port_listeners(port: int) -> tuple[str | None, int]:
    """Return (output, rc). rc==2 means neither ss nor lsof available."""
    if _command_exists("ss"):
        result = subprocess.run(
            ["ss", "-H", "-ltnp", f"sport = :{port}"],
            capture_output=True,
            text=True,
        )
        return result.stdout, 0
    if _command_exists("lsof"):
        result = subprocess.run(
            ["lsof", "-nP", "-iTCP", f"{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
        )
        return result.stdout, 0
    return None, 2


def _docker_container_running(name: str) -> bool:
    if not _command_exists("docker"):
        return False
    result = subprocess.run(
        ["docker", "ps", "--filter", f"name=^/{name}$", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == name


def _docker_container_publishes_port(name: str, port: int) -> bool:
    if not _command_exists("docker"):
        return False
    result = subprocess.run(
        ["docker", "ps", "--filter", f"name=^/{name}$", "--format", "{{.Names}} {{.Ports}}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    line = result.stdout.strip()
    # Heuristic: port appears in the ports column
    import re
    pattern = rf"(:|->){port}(/|->|$)|:{port}->"
    return bool(re.search(pattern, line))


def check_os() -> CheckResult:
    kernel = platform.system()
    if kernel == "Darwin":
        return CheckResult("os", "ok", True, "Mac detected")
    if kernel != "Linux":
        return CheckResult("os", "fail", True, f"unsupported OS: {kernel or 'unknown'}")

    distro = ""
    version = ""
    if _command_exists("lsb_release"):
        try:
            dresult = subprocess.run(
                ["lsb_release", "-is"], capture_output=True, text=True, check=True
            )
            vresult = subprocess.run(
                ["lsb_release", "-rs"], capture_output=True, text=True, check=True
            )
            distro = dresult.stdout.strip()
            version = vresult.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    else:
        try:
            os_release = Path("/etc/os-release")
            if os_release.exists():
                text = os_release.read_text()
                for line in text.splitlines():
                    if line.startswith("ID="):
                        distro = line.split("=", 1)[1].strip().strip('"')
                    elif line.startswith("VERSION_ID="):
                        version = line.split("=", 1)[1].strip().strip('"')
        except OSError:
            pass

    distro_lower = distro.lower()
    if distro_lower == "ubuntu":
        return CheckResult("os", "ok", True, f"Ubuntu {version or 'unknown'} detected")
    return CheckResult(
        "os",
        "fail",
        True,
        f"Linux distro must be Ubuntu for the documented helper path; found {distro or 'unknown'}",
    )


def check_arch() -> CheckResult:
    raw = platform.machine()
    normalized = _normalize_arch(raw)
    if normalized:
        return CheckResult("architecture", "ok", False, f"{normalized} ({raw})")
    return CheckResult(
        "architecture",
        "fail",
        False,
        f"unsupported architecture: {raw or 'unknown'}; expected amd64 or arm64",
    )


def check_ram() -> CheckResult:
    mb: int | None = None
    try:
        meminfo = Path("/proc/meminfo")
        if meminfo.exists():
            text = meminfo.read_text()
            for line in text.splitlines():
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    kb = int(parts[1])
                    mb = kb // 1024
                    break
    except (OSError, ValueError):
        pass

    if mb is None and _command_exists("sysctl"):
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                check=True,
            )
            bytes_str = result.stdout.strip()
            if bytes_str.isdigit():
                mb = int(bytes_str) // 1024 // 1024
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            pass

    if mb is None:
        return CheckResult("ram", "warn", False, "could not determine RAM")
    if mb < 2048:
        return CheckResult("ram", "fail", False, f"{mb} MB available; minimum is 2048 MB")
    if mb < 4096:
        return CheckResult("ram", "warn", False, f"{mb} MB available; 4 GB or more is recommended")
    return CheckResult("ram", "ok", False, f"{mb} MB available")


def check_disk(data_root: str) -> CheckResult:
    probe = Path(data_root)
    while not probe.exists() and probe != Path("/"):
        probe = probe.parent

    try:
        result = subprocess.run(
            ["df", "-Pk", str(probe)],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.strip().splitlines()
        if len(lines) >= 2:
            free_kb = int(lines[1].split()[3])
            free_gb = free_kb // 1024 // 1024
            if free_gb < 20:
                return CheckResult(
                    "disk",
                    "warn",
                    False,
                    f"{free_gb} GB free at {probe}; 20 GB or more is recommended for {data_root}",
                )
            return CheckResult("disk", "ok", False, f"{free_gb} GB free at {probe}")
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError, IndexError):
        pass

    return CheckResult("disk", "warn", False, f"could not determine free space for {data_root}")


def check_docker() -> CheckResult:
    if not _command_exists("docker"):
        return CheckResult("docker", "fail", True, "docker command is missing")
    result = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return CheckResult("docker", "ok", True, "daemon is reachable")
    return CheckResult("docker", "fail", True, "docker command exists but daemon is not reachable")


def check_compose() -> CheckResult:
    if not _command_exists("docker"):
        return CheckResult("compose", "fail", True, "docker command is missing")
    result = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return CheckResult("compose", "ok", True, result.stdout.strip())
    return CheckResult("compose", "fail", True, "Docker Compose v2 is not available through 'docker compose'")


def check_cloudflared_binary() -> CheckResult:
    if _command_exists("cloudflared"):
        return CheckResult("cloudflared_cli", "ok", False, "cloudflared is on PATH")
    local_bin = Path.home() / ".local" / "bin" / "cloudflared"
    if local_bin.exists() and local_bin.is_file():
        return CheckResult("cloudflared_cli", "ok", False, f"cloudflared is available at {local_bin}")
    return CheckResult(
        "cloudflared_cli",
        "warn",
        False,
        "cloudflared host CLI is missing; Step 00 should install it before Step 40",
    )


def check_public_ports() -> CheckResult:
    failures = 0
    messages: list[str] = []

    for port in (80, 443):
        listeners, rc = _port_listeners(port)
        if rc == 2:
            return CheckResult(
                "public_ports",
                "warn",
                True,
                "neither ss nor lsof is available to inspect ports 80/443",
            )

        if not listeners:
            messages.append(f"{port}=free")
            continue

        if "caddy" in listeners.lower() or _docker_container_publishes_port("caddy", port):
            messages.append(f"{port}=owned by caddy")
        else:
            messages.append(f"{port}=conflict")
            failures += 1

    if failures == 0:
        return CheckResult("public_ports", "ok", True, " ".join(messages))
    return CheckResult(
        "public_ports",
        "fail",
        True,
        f"ports 80/443 must be free or owned by Rakkib caddy; {' '.join(messages)}",
    )


def check_ssh_port() -> CheckResult:
    listeners, rc = _port_listeners(22)
    if rc == 2:
        return CheckResult("ssh_port", "warn", False, "neither ss nor lsof is available to inspect port 22")
    if listeners:
        return CheckResult("ssh_port", "ok", False, "port 22 has a listener")
    return CheckResult(
        "ssh_port",
        "warn",
        False,
        "port 22 is not listening; SSH over Cloudflare will not work until SSH is enabled",
    )


def check_domain_dns(domain: str) -> CheckResult:
    if not domain or domain == "null":
        return CheckResult("dns", "warn", False, "domain is not recorded yet")
    if not _command_exists("dig"):
        return CheckResult("dns", "warn", False, f"dig is not installed; cannot resolve {domain}")

    ips: list[str] = []
    for qtype in ("A", "AAAA"):
        result = subprocess.run(
            ["dig", "+short", domain, qtype],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if line:
                    ips.append(line)

    if ips:
        return CheckResult("dns", "ok", False, f"{domain} resolves: {' '.join(ips)}")
    return CheckResult("dns", "warn", False, f"{domain} does not currently resolve")


def check_cloudflare_readiness(state: State) -> list[CheckResult]:
    results: list[CheckResult] = []
    zone_in = state.get("cloudflare.zone_in_cloudflare")
    if zone_in is False:
        results.append(
            CheckResult(
                "cloudflare_zone",
                "warn",
                False,
                "domain is not yet active in Cloudflare for this install; Step 40 public routing will stay blocked",
            )
        )
    elif zone_in is True:
        results.append(CheckResult("cloudflare_zone", "ok", False, "domain is marked as active in Cloudflare"))
    else:
        results.append(CheckResult("cloudflare_zone", "warn", False, "Cloudflare zone state is not recorded yet"))

    auth_method = state.get("cloudflare.auth_method")
    if not auth_method or auth_method == "null":
        results.append(CheckResult("cloudflare_auth", "warn", False, "Cloudflare auth method is not recorded yet"))
        return results

    data_root = state.get("data_root", "/srv")
    if auth_method == "browser_login":
        cert_path = Path(data_root) / "data" / "cloudflared" / "cert.pem"
        if cert_path.exists():
            results.append(
                CheckResult(
                    "cloudflare_auth",
                    "ok",
                    False,
                    f"browser-login auth cert is present at {cert_path}",
                )
            )
        else:
            results.append(
                CheckResult(
                    "cloudflare_auth",
                    "warn",
                    False,
                    f"browser-login auth cert is missing at {cert_path}; Step 40 will need cloudflared tunnel login",
                )
            )
    elif auth_method == "api_token":
        results.append(
            CheckResult(
                "cloudflare_auth",
                "ok",
                False,
                "advanced API token mode recorded; token should be requested only during Step 40",
            )
        )
    elif auth_method == "existing_tunnel":
        results.append(CheckResult("cloudflare_auth", "ok", False, "existing tunnel mode recorded"))
    else:
        results.append(
            CheckResult(
                "cloudflare_auth",
                "warn",
                False,
                f"unrecognized Cloudflare auth method recorded: {auth_method}",
            )
        )

    creds_path = state.get("cloudflare.tunnel_creds_host_path")
    tunnel_uuid = state.get("cloudflare.tunnel_uuid")
    if creds_path and creds_path != "null":
        if Path(creds_path).exists():
            results.append(
                CheckResult(
                    "cloudflare_creds",
                    "ok",
                    False,
                    f"tunnel credentials JSON is present at {creds_path}",
                )
            )
        else:
            results.append(
                CheckResult(
                    "cloudflare_creds",
                    "warn",
                    False,
                    f"tunnel credentials JSON is recorded but missing at {creds_path}",
                )
            )
    elif tunnel_uuid and tunnel_uuid != "null":
        results.append(
            CheckResult(
                "cloudflare_creds",
                "warn",
                False,
                "tunnel UUID is recorded but the standardized credentials path is not recorded yet",
            )
        )
    else:
        results.append(
            CheckResult(
                "cloudflare_creds",
                "warn",
                False,
                "tunnel credentials are not recorded yet; Step 40 must create or recover them",
            )
        )

    return results


def check_conflicts() -> CheckResult:
    conflicts: list[str] = []

    if _command_exists("systemctl"):
        for service in ("nginx", "apache2", "httpd", "postgresql"):
            result = subprocess.run(
                ["systemctl", "is-active", "--quiet", service],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                conflicts.append(f"active systemd service: {service}")

    pg_listeners, rc = _port_listeners(5432)
    if rc != 2 and pg_listeners:
        if _docker_container_running("postgres"):
            pass
        elif "docker" not in pg_listeners.lower() and "postgres" not in pg_listeners.lower():
            conflicts.append("port 5432 listener is not clearly Rakkib postgres")
        else:
            conflicts.append("port 5432 is already listening before the Rakkib postgres container is running")

    if not conflicts:
        return CheckResult("conflicts", "ok", False, "no obvious nginx/apache/host-postgres conflicts found")
    return CheckResult("conflicts", "warn", False, "; ".join(conflicts))


def run_checks(state: State) -> list[CheckResult]:
    """Run all diagnostic checks and return results."""
    data_root = state.get("data_root") or "/srv"
    domain = state.get("domain") or ""

    results: list[CheckResult] = []
    results.append(check_os())
    results.append(check_arch())
    results.append(check_ram())
    results.append(check_disk(data_root))
    results.append(check_docker())
    results.append(check_compose())
    results.append(check_cloudflared_binary())
    results.append(check_public_ports())
    results.append(check_ssh_port())
    results.append(check_domain_dns(domain))
    results.extend(check_cloudflare_readiness(state))
    results.append(check_conflicts())
    return results


def to_json(checks: list[CheckResult]) -> str:
    """Emit JSON matching the original bash script shape."""
    fail_count = sum(1 for c in checks if c.status == "fail")
    ok_count = sum(1 for c in checks if c.status == "ok")
    warn_count = sum(1 for c in checks if c.status == "warn")
    payload = {
        "ok": fail_count == 0,
        "summary": {"ok": ok_count, "warn": warn_count, "fail": fail_count},
        "checks": [c.to_dict() for c in checks],
    }
    return json.dumps(payload)


def summary_text(checks: list[CheckResult]) -> str:
    fail_count = sum(1 for c in checks if c.status == "fail")
    ok_count = sum(1 for c in checks if c.status == "ok")
    warn_count = sum(1 for c in checks if c.status == "warn")
    return f"doctor: {ok_count} ok, {warn_count} warn, {fail_count} fail"


def attempt_fix_docker() -> str:
    """Attempt to install Docker. Returns a message describing the result."""
    if platform.system() != "Linux":
        return "Automatic Docker installation is only supported on Linux."

    if not _command_exists("curl"):
        return "curl is required but not found. Install curl first."

    result = subprocess.run(
        ["sh", "-c", "curl -fsSL https://get.docker.com | sh"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return "Docker installed via get.docker.com. You may need to start the service with 'sudo systemctl start docker'."
    return f"get.docker.com install failed: {result.stderr.strip() or 'unknown error'}"


def attempt_fix_compose() -> str:
    """Install docker compose v2 plugin. Returns a message describing the result."""
    machine = platform.machine().lower()
    arch_map = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}
    arch = arch_map.get(machine)
    if not arch:
        return f"Unsupported architecture for compose plugin: {machine}"

    compose_version = "v2.35.1"
    url = f"https://github.com/docker/compose/releases/download/{compose_version}/docker-compose-linux-{arch}"

    try:
        result = subprocess.run(
            ["sudo", "mkdir", "-p", "/usr/local/lib/docker/cli-plugins"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return f"Failed to create cli-plugins directory: {result.stderr.strip() or 'unknown error'}"

        result = subprocess.run(
            ["sudo", "curl", "-fsSL", "-o", "/usr/local/lib/docker/cli-plugins/docker-compose", url],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return f"Failed to download docker compose: {result.stderr.strip() or 'unknown error'}"

        subprocess.run(
            ["sudo", "chmod", "+x", "/usr/local/lib/docker/cli-plugins/docker-compose"],
            capture_output=True,
            text=True,
        )

        verify = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
        )
        if verify.returncode == 0:
            return "docker compose plugin installed successfully."
        return "docker compose plugin installed but 'docker compose version' failed. Try relogging or opening a new shell."

    except FileNotFoundError as e:
        return f"Required command not found: {e}"


def attempt_fix_cloudflared() -> str:
    """Attempt to install cloudflared. Returns a message describing the result."""
    local_bin = Path.home() / ".local" / "bin"
    local_bin.mkdir(parents=True, exist_ok=True)

    arch = _normalize_arch(platform.machine()) or "amd64"
    kernel = platform.system().lower()
    if kernel == "darwin":
        kernel = "darwin"
    else:
        kernel = "linux"

    url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-{kernel}-{arch}"
    if kernel == "darwin":
        url += ".tgz"
    else:
        url += ".deb"

    try:
        if kernel == "linux" and _command_exists("dpkg"):
            deb_path = local_bin / "cloudflared.deb"
            result = subprocess.run(
                ["curl", "-fsSL", "-o", str(deb_path), url],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                result = subprocess.run(
                    ["sudo", "dpkg", "-i", str(deb_path)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 or result.returncode == 1:
                    # dpkg may exit 1 if dependencies missing; still likely installed
                    return f"cloudflared installed via dpkg from {url}"
        # Fallback: direct binary download
        result = subprocess.run(
            ["curl", "-fsSL", "-o", str(local_bin / "cloudflared"), url.replace(".deb", "")],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            (local_bin / "cloudflared").chmod(0o755)
            return f"cloudflared downloaded to {local_bin / 'cloudflared'}"
        return f"cloudflared download failed: {result.stderr.strip() or 'unknown error'}"
    except FileNotFoundError:
        return "curl is not available; cannot install cloudflared automatically."


def process_owners_for_ports() -> dict[int, str]:
    """Return a mapping of port -> process info for ports 80 and 443."""
    owners: dict[int, str] = {}
    for port in (80, 443):
        listeners, rc = _port_listeners(port)
        if rc == 2:
            owners[port] = "unable to determine (ss/lsof missing)"
        elif listeners:
            # Take first non-empty line as owner info
            lines = [ln.strip() for ln in listeners.splitlines() if ln.strip()]
            owners[port] = lines[0] if lines else "unknown"
        else:
            owners[port] = "free"
    return owners
