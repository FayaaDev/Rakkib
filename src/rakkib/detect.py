"""Host detection helpers.

Detect platform, architecture, LAN IP, Docker status, and privilege context.
"""

from __future__ import annotations

import platform
import shutil
import socket
import subprocess
from dataclasses import dataclass
from typing import Literal


Platform = Literal["linux", "mac"]
Arch = Literal["amd64", "arm64"]


@dataclass
class HostInfo:
    """Snapshot of host environment."""

    platform: Platform
    arch: Arch
    lan_ip: str | None
    docker_installed: bool
    privilege_mode: Literal["root", "sudo"]
    privilege_strategy: Literal["on_demand", "root_process"]


def detect_platform() -> Platform:
    """Return 'linux' or 'mac'."""
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "mac"
    raise RuntimeError(f"Unsupported platform: {system}")


def detect_arch() -> Arch:
    """Return normalized architecture."""
    machine = platform.machine().lower()
    mapping = {
        "x86_64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    if machine not in mapping:
        raise RuntimeError(f"Unsupported architecture: {machine}")
    return mapping[machine]


def detect_lan_ip() -> str | None:
    """Attempt to detect the primary LAN IP address."""
    # Linux: hostname -I
    # Mac: ipconfig getifaddr en0
    try:
        if detect_platform() == "linux":
            result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True,
                text=True,
                check=True,
            )
            ips = result.stdout.strip().split()
            return ips[0] if ips else None
        else:
            result = subprocess.run(
                ["ipconfig", "getifaddr", "en0"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def is_docker_installed() -> bool:
    """Return True if the docker CLI is available."""
    return shutil.which("docker") is not None


def detect_privilege() -> tuple[Literal["root", "sudo"], Literal["on_demand", "root_process"]]:
    """Detect whether we are running as root or a normal user."""
    try:
        euid = subprocess.run(["id", "-u"], capture_output=True, text=True, check=True)
        if euid.stdout.strip() == "0":
            return "root", "root_process"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return "sudo", "on_demand"


def gather_host_info() -> HostInfo:
    """Collect all host detection information."""
    return HostInfo(
        platform=detect_platform(),
        arch=detect_arch(),
        lan_ip=detect_lan_ip(),
        docker_installed=is_docker_installed(),
        privilege_mode=detect_privilege()[0],
        privilege_strategy=detect_privilege()[1],
    )
