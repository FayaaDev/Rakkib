"""Tests for rakkib.doctor."""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rakkib.doctor import (
    CheckResult,
    attempt_fix_cloudflared,
    attempt_fix_docker,
    attempt_fix_compose,
    check_arch,
    check_cloudflared_binary,
    check_compose,
    check_conflicts,
    check_disk,
    check_docker,
    check_domain_dns,
    check_os,
    check_public_ports,
    check_ram,
    check_ssh_port,
    process_owners_for_ports,
    run_checks,
    summary_text,
    to_json,
    wait_for_apt_locks,
)
from rakkib.state import State


class TestCheckOs:
    @patch("platform.system", return_value="Darwin")
    def test_mac(self, _mock: MagicMock):
        result = check_os()
        assert result.status == "ok"
        assert result.blocking is True
        assert "Mac" in result.message

    @patch("platform.system", return_value="Windows")
    def test_unsupported(self, _mock: MagicMock):
        result = check_os()
        assert result.status == "fail"
        assert "unsupported OS" in result.message

    @patch("platform.system", return_value="Linux")
    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    def test_ubuntu(self, mock_run: MagicMock, _cmd_exists: MagicMock, _system: MagicMock):
        def side_effect(cmd, **kwargs):
            if "-is" in cmd:
                return MagicMock(stdout="Ubuntu\n", returncode=0)
            return MagicMock(stdout="22.04\n", returncode=0)
        mock_run.side_effect = side_effect
        result = check_os()
        assert result.status == "ok"
        assert "Ubuntu" in result.message

    @patch("platform.system", return_value="Linux")
    @patch("rakkib.doctor._command_exists", return_value=False)
    def test_non_ubuntu(self, _cmd_exists: MagicMock, _system: MagicMock, tmp_path: Path, monkeypatch):
        # Write fake /etc/os-release
        os_release = tmp_path / "os-release"
        os_release.write_text('ID=debian\nVERSION_ID="11"\n')
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=os_release.read_text()):
                result = check_os()
        assert result.status == "fail"
        assert "Ubuntu" in result.message


class TestCheckArch:
    @patch("platform.machine", return_value="x86_64")
    def test_amd64(self, _mock: MagicMock):
        result = check_arch()
        assert result.status == "ok"
        assert "amd64" in result.message

    @patch("platform.machine", return_value="armv7l")
    def test_unsupported(self, _mock: MagicMock):
        result = check_arch()
        assert result.status == "fail"
        assert "unsupported" in result.message


class TestCheckRam:
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="MemTotal:       16384000 kB\n")
    def test_high_ram(self, _exists: MagicMock, _text: MagicMock):
        result = check_ram()
        assert result.status == "ok"

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="MemTotal:       1024000 kB\n")
    def test_low_ram(self, _exists: MagicMock, _text: MagicMock):
        result = check_ram()
        assert result.status == "fail"

    @patch("pathlib.Path.exists", return_value=False)
    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    def test_mac_ram(self, mock_run: MagicMock, _cmd: MagicMock, _exists: MagicMock):
        mock_run.return_value = MagicMock(stdout="17179869184\n", returncode=0)
        result = check_ram()
        assert result.status == "ok"
        assert "MB" in result.message

    @patch("pathlib.Path.exists", return_value=False)
    @patch("rakkib.doctor._command_exists", return_value=False)
    def test_cannot_determine(self, _cmd: MagicMock, _exists: MagicMock):
        result = check_ram()
        assert result.status == "warn"


class TestCheckDisk:
    @patch("subprocess.run")
    def test_ok(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(
            stdout="Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/sda1 100000000 1000 99999000 2% /\n",
            returncode=0,
        )
        result = check_disk("/srv")
        assert result.status == "ok"

    @patch("subprocess.run")
    def test_low(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(
            stdout="Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/sda1 100000 99000 1000 99% /\n",
            returncode=0,
        )
        result = check_disk("/srv")
        assert result.status == "warn"

    @patch("subprocess.run")
    def test_unknown(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(stdout="", returncode=1)
        result = check_disk("/srv")
        assert result.status == "warn"


class TestCheckDocker:
    @patch("rakkib.doctor._command_exists", return_value=False)
    def test_missing(self, _mock: MagicMock):
        result = check_docker()
        assert result.status == "fail"
        assert "missing" in result.message

    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    def test_unreachable(self, mock_run: MagicMock, _cmd: MagicMock):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
        result = check_docker()
        assert result.status == "fail"

    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    def test_ok(self, mock_run: MagicMock, _cmd: MagicMock):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = check_docker()
        assert result.status == "ok"


class TestCheckCompose:
    @patch("rakkib.doctor._command_exists", return_value=False)
    def test_missing_docker(self, _mock: MagicMock):
        result = check_compose()
        assert result.status == "fail"
        assert "docker command is missing" in result.message

    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    def test_ok(self, mock_run: MagicMock, _cmd: MagicMock):
        mock_run.return_value = MagicMock(returncode=0, stdout="Docker Compose version v2.24\n")
        result = check_compose()
        assert result.status == "ok"
        assert "v2.24" in result.message

    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    def test_fail(self, mock_run: MagicMock, _cmd: MagicMock):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
        result = check_compose()
        assert result.status == "fail"


class TestCheckCloudflaredBinary:
    @patch("shutil.which", return_value="/usr/bin/cloudflared")
    def test_on_path(self, _mock: MagicMock):
        result = check_cloudflared_binary()
        assert result.status == "ok"

    @patch("shutil.which", return_value=None)
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    def test_local_bin(self, _is_file: MagicMock, _exists: MagicMock, _which: MagicMock):
        result = check_cloudflared_binary()
        assert result.status == "ok"

    @patch("shutil.which", return_value=None)
    @patch("pathlib.Path.exists", return_value=False)
    def test_missing(self, _exists: MagicMock, _which: MagicMock):
        result = check_cloudflared_binary()
        assert result.status == "warn"


class TestCheckPublicPorts:
    @patch("rakkib.doctor._port_listeners", return_value=("", 0))
    def test_free(self, _mock: MagicMock):
        result = check_public_ports()
        assert result.status == "ok"
        assert "free" in result.message

    @patch("rakkib.doctor._port_listeners", side_effect=[("LISTEN 0.0.0.0:80 users:((\"caddy\"))", 0), ("", 0)])
    def test_owned_by_caddy(self, _mock: MagicMock):
        result = check_public_ports()
        assert result.status == "ok"
        assert "owned by caddy" in result.message

    @patch("rakkib.doctor._docker_container_publishes_port", return_value=False)
    @patch("rakkib.doctor._port_listeners", side_effect=[("LISTEN 0.0.0.0:80 users:((\"nginx\"))", 0), ("", 0)])
    def test_conflict(self, _mock_pl: MagicMock, _mock_dcpp: MagicMock):
        result = check_public_ports()
        assert result.status == "fail"
        assert "conflict" in result.message

    @patch("rakkib.doctor._port_listeners", return_value=(None, 2))
    def test_no_tools(self, _mock: MagicMock):
        result = check_public_ports()
        assert result.status == "warn"


class TestCheckSshPort:
    @patch("rakkib.doctor._port_listeners", return_value=("LISTEN 0.0.0.0:22 users:((\"sshd\"))", 0))
    def test_listening(self, _mock: MagicMock):
        result = check_ssh_port()
        assert result.status == "ok"

    @patch("rakkib.doctor._port_listeners", return_value=("", 0))
    def test_not_listening(self, _mock: MagicMock):
        result = check_ssh_port()
        assert result.status == "warn"

    @patch("rakkib.doctor._port_listeners", return_value=(None, 2))
    def test_no_tools(self, _mock: MagicMock):
        result = check_ssh_port()
        assert result.status == "warn"


class TestCheckDomainDns:
    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    def test_resolves(self, mock_run: MagicMock, _cmd: MagicMock):
        mock_run.return_value = MagicMock(returncode=0, stdout="1.2.3.4\n")
        result = check_domain_dns("example.com")
        assert result.status == "ok"
        assert "1.2.3.4" in result.message

    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    def test_no_resolve(self, mock_run: MagicMock, _cmd: MagicMock):
        mock_run.return_value = MagicMock(returncode=0, stdout="\n")
        result = check_domain_dns("example.com")
        assert result.status == "warn"

    def test_no_domain(self):
        result = check_domain_dns("")
        assert result.status == "warn"

    @patch("rakkib.doctor._command_exists", return_value=False)
    def test_no_dig(self, _cmd: MagicMock):
        result = check_domain_dns("example.com")
        assert result.status == "warn"
        assert "dig is not installed" in result.message


class TestCheckConflicts:
    @patch("rakkib.doctor._command_exists", return_value=False)
    @patch("rakkib.doctor._port_listeners", return_value=("", 0))
    def test_none(self, _pl: MagicMock, _cmd: MagicMock):
        result = check_conflicts()
        assert result.status == "ok"

    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    @patch("rakkib.doctor._port_listeners", return_value=("", 0))
    def test_nginx_active(self, _pl: MagicMock, mock_run: MagicMock, _cmd: MagicMock):
        mock_run.return_value = MagicMock(returncode=0)
        result = check_conflicts()
        assert result.status == "warn"
        assert "nginx" in result.message


class TestRunChecks:
    def test_runs_all(self):
        state = State({"domain": "example.com", "data_root": "/srv"})
        with patch("rakkib.doctor.check_os") as mock_os, \
             patch("rakkib.doctor.check_arch") as mock_arch:
            from rakkib.doctor import CheckResult
            mock_os.return_value = CheckResult("os", "ok", True, "")
            mock_arch.return_value = CheckResult("architecture", "ok", False, "")
            results = run_checks(state)
            assert len(results) >= 12
            names = [r.name for r in results]
            assert "os" in names
            assert "architecture" in names


class TestJson:
    def test_to_json(self):
        checks = [
            CheckResult("a", "ok", False, ""),
            CheckResult("b", "warn", False, ""),
            CheckResult("c", "fail", True, ""),
        ]
        text = to_json(checks)
        data = json.loads(text)
        assert data["ok"] is False
        assert data["summary"]["fail"] == 1
        assert data["summary"]["ok"] == 1
        assert data["summary"]["warn"] == 1
        assert len(data["checks"]) == 3


class TestSummaryText:
    def test_summary(self):
        checks = [
            CheckResult("a", "ok", False, ""),
            CheckResult("b", "warn", False, ""),
            CheckResult("c", "fail", True, ""),
        ]
        assert summary_text(checks) == "doctor: 1 ok, 1 warn, 1 fail"


class TestAttemptFixDocker:
    @patch("platform.system", return_value="Darwin")
    def test_skips_mac(self, _mock: MagicMock):
        msg = attempt_fix_docker()
        assert "only supported on Linux" in msg

    @patch("platform.system", return_value="Linux")
    @patch("rakkib.doctor.wait_for_apt_locks", return_value=None)
    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    def test_get_docker_success(
        self,
        mock_run: MagicMock,
        _cmd: MagicMock,
        mock_wait: MagicMock,
        _system: MagicMock,
    ):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        msg = attempt_fix_docker()
        assert "get.docker.com" in msg
        mock_wait.assert_called_once()
        assert mock_run.call_args_list[0].kwargs["env"]["DEBIAN_FRONTEND"] == "noninteractive"
        assert mock_run.call_args_list[0].kwargs["env"]["NEEDRESTART_MODE"] == "a"

    @patch("platform.system", return_value="Linux")
    @patch("rakkib.doctor.wait_for_apt_locks", return_value=None)
    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    def test_get_docker_failure(
        self,
        mock_run: MagicMock,
        _cmd: MagicMock,
        _wait: MagicMock,
        _system: MagicMock,
    ):
        mock_run.return_value = MagicMock(returncode=1, stderr="network error")
        msg = attempt_fix_docker()
        assert "failed" in msg

    @patch("platform.system", return_value="Linux")
    @patch(
        "rakkib.doctor.wait_for_apt_locks",
        return_value="Timed out waiting for apt/dpkg locks",
    )
    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    def test_apt_lock_timeout_skips_get_docker(
        self,
        mock_run: MagicMock,
        _cmd: MagicMock,
        _wait: MagicMock,
        _system: MagicMock,
    ):
        msg = attempt_fix_docker()
        assert "Timed out waiting" in msg
        mock_run.assert_not_called()

    @patch("platform.system", return_value="Linux")
    @patch("rakkib.doctor._command_exists", return_value=False)
    def test_no_curl(self, _cmd: MagicMock, _system: MagicMock):
        msg = attempt_fix_docker()
        assert "curl is required" in msg


class TestWaitForAptLocks:
    @patch("rakkib.doctor._locked_apt_files", return_value=[])
    def test_returns_none_when_unlocked(self, _locks: MagicMock):
        assert wait_for_apt_locks(timeout=0, interval=0) is None

    @patch("time.sleep")
    @patch("time.monotonic", side_effect=[0, 0, 2])
    @patch("rakkib.doctor._locked_apt_files", return_value=["/var/lib/dpkg/lock-frontend"])
    def test_timeout_is_actionable(
        self,
        _locks: MagicMock,
        _time: MagicMock,
        _sleep: MagicMock,
    ):
        msg = wait_for_apt_locks(timeout=1, interval=0)
        assert msg is not None
        assert "Ubuntu automatic updates" in msg
        assert "sudo systemctl stop unattended-upgrades" in msg

    @patch("time.sleep")
    @patch("time.monotonic", side_effect=[0, 0, 2])
    @patch("rakkib.doctor._locked_apt_files", return_value=["/var/lib/dpkg/lock-frontend"])
    def test_notifies_once_when_locked(
        self,
        _locks: MagicMock,
        _time: MagicMock,
        _sleep: MagicMock,
    ):
        notices: list[list[str]] = []
        wait_for_apt_locks(timeout=1, interval=0, on_wait=notices.append)
        assert notices == [["/var/lib/dpkg/lock-frontend"]]


class TestAttemptFixCompose:
    @patch("rakkib.doctor.wait_for_apt_locks", return_value=None)
    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("platform.machine", return_value="x86_64")
    @patch("subprocess.run")
    def test_install_success(
        self,
        mock_run: MagicMock,
        _machine: MagicMock,
        _cmd: MagicMock,
        mock_wait: MagicMock,
    ):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        msg = attempt_fix_compose()
        assert "docker-compose-plugin installed via apt" in msg
        mock_wait.assert_called_once()
        assert "DPkg::Lock::Timeout=900" in mock_run.call_args.args[0]
        assert "DEBIAN_FRONTEND=noninteractive" in mock_run.call_args.args[0]
        assert "NEEDRESTART_SUSPEND=1" in mock_run.call_args.args[0]
        assert mock_run.call_args.kwargs["env"]["NEEDRESTART_MODE"] == "a"

    @patch("rakkib.doctor.wait_for_apt_locks", return_value="Timed out waiting for apt/dpkg locks")
    @patch("rakkib.doctor._command_exists", return_value=True)
    @patch("subprocess.run")
    def test_apt_lock_timeout_skips_compose_install(
        self,
        mock_run: MagicMock,
        _cmd: MagicMock,
        _wait: MagicMock,
    ):
        msg = attempt_fix_compose()
        assert "Timed out waiting" in msg
        mock_run.assert_not_called()

    @patch("platform.machine", return_value="x86_64")
    @patch("subprocess.run")
    def test_mkdir_fails(self, mock_run: MagicMock, _machine: MagicMock):
        mock_run.return_value = MagicMock(returncode=1, stderr="permission denied")
        msg = attempt_fix_compose()
        assert "cli-plugins directory" in msg

    @patch("platform.machine", return_value="x86_64")
    @patch("subprocess.run")
    def test_download_fails(self, mock_run: MagicMock, _machine: MagicMock):
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr=""),
            MagicMock(returncode=1, stderr="network error"),
        ]
        msg = attempt_fix_compose()
        assert "download" in msg.lower() and "failed" in msg.lower()

    @patch("platform.machine", return_value="x86_64")
    @patch("subprocess.run")
    def test_install_verify_fails(self, mock_run: MagicMock, _machine: MagicMock):
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr=""),
            MagicMock(returncode=0, stderr=""),
            MagicMock(returncode=0, stderr=""),
            MagicMock(returncode=1, stdout="", stderr="not found"),
        ]
        msg = attempt_fix_compose()
        assert "failed" in msg.lower()

    def test_unsupported_arch(self):
        with patch("platform.machine", return_value="mips"):
            msg = attempt_fix_compose()
            assert "Unsupported architecture" in msg


class TestAttemptFixCloudflared:
    @patch("subprocess.run")
    @patch("pathlib.Path.mkdir")
    def test_download_success(self, _mkdir: MagicMock, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        msg = attempt_fix_cloudflared()
        assert "downloaded" in msg or "installed" in msg

    @patch("subprocess.run")
    def test_download_failure(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=1, stderr="network error")
        msg = attempt_fix_cloudflared()
        assert "failed" in msg


class TestProcessOwnersForPorts:
    @patch("rakkib.doctor._port_listeners", side_effect=[("LISTEN 0.0.0.0:80 users:((nginx))", 0), ("", 0)])
    def test_owners(self, _mock: MagicMock):
        owners = process_owners_for_ports()
        assert owners[80] == "LISTEN 0.0.0.0:80 users:((nginx))"
        assert owners[443] == "free"
