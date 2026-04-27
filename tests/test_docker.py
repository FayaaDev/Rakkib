"""Tests for rakkib.docker."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rakkib.docker import (
    DockerError,
    compose_down,
    compose_pull,
    compose_up,
    container_publishes_port,
    container_running,
    create_network,
    health_check,
    network_exists,
)


class TestComposeUp:
    @patch("rakkib.docker._run")
    def test_basic(self, mock_run: MagicMock):
        compose_up("/tmp/proj")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[:4] == ["docker", "compose", "--project-directory", "/tmp/proj"]
        assert "up" in cmd
        assert "-d" in cmd

    @patch("rakkib.docker._run")
    def test_with_services(self, mock_run: MagicMock):
        compose_up("/tmp/proj", services=["web", "db"])
        cmd = mock_run.call_args[0][0]
        assert "web" in cmd
        assert "db" in cmd

    @patch("rakkib.docker._run")
    def test_with_profiles(self, mock_run: MagicMock):
        compose_up("/tmp/proj", profiles=["prod", "debug"])
        cmd = mock_run.call_args[0][0]
        assert cmd.count("--profile") == 2
        assert "prod" in cmd
        assert "debug" in cmd

    @patch("rakkib.docker._run")
    def test_no_detach(self, mock_run: MagicMock):
        compose_up("/tmp/proj", detach=False)
        cmd = mock_run.call_args[0][0]
        assert "-d" not in cmd

    @patch("rakkib.docker._run")
    def test_log_path(self, mock_run: MagicMock):
        compose_up("/tmp/proj", log_path="/tmp/log.txt")
        _, kwargs = mock_run.call_args
        assert kwargs.get("log_path") == "/tmp/log.txt"


class TestComposePull:
    @patch("rakkib.docker._run")
    def test_basic(self, mock_run: MagicMock):
        compose_pull("/tmp/proj")
        cmd = mock_run.call_args[0][0]
        assert "pull" in cmd

    @patch("rakkib.docker._run")
    def test_with_services(self, mock_run: MagicMock):
        compose_pull("/tmp/proj", services=["web", "db"])
        cmd = mock_run.call_args[0][0]
        assert "web" in cmd
        assert "db" in cmd


class TestComposeDown:
    @patch("rakkib.docker._run")
    def test_basic(self, mock_run: MagicMock):
        compose_down("/tmp/proj")
        cmd = mock_run.call_args[0][0]
        assert "down" in cmd
        assert "--volumes" not in cmd

    @patch("rakkib.docker._run")
    def test_with_volumes(self, mock_run: MagicMock):
        compose_down("/tmp/proj", volumes=True)
        cmd = mock_run.call_args[0][0]
        assert "--volumes" in cmd

    @patch("rakkib.docker._run")
    def test_log_path(self, mock_run: MagicMock):
        compose_down("/tmp/proj", log_path="/tmp/log.txt")
        _, kwargs = mock_run.call_args
        assert kwargs.get("log_path") == "/tmp/log.txt"


class TestHealthCheck:
    @patch("rakkib.docker._run")
    @patch("rakkib.docker.time")
    def test_healthy_immediately(self, mock_time: MagicMock, mock_run: MagicMock):
        mock_run.return_value = MagicMock(stdout="healthy\n")
        mock_time.monotonic.side_effect = [0, 1, 2]
        assert health_check("mycontainer", timeout=10) is True

    @patch("rakkib.docker._run")
    @patch("rakkib.docker.time")
    def test_becomes_healthy_after_poll(self, mock_time: MagicMock, mock_run: MagicMock):
        mock_run.side_effect = [
            MagicMock(stdout="starting\n"),
            MagicMock(stdout="healthy\n"),
        ]
        mock_time.monotonic.side_effect = [0, 1, 2, 3]
        assert health_check("mycontainer", timeout=10) is True

    @patch("rakkib.docker._run")
    @patch("rakkib.docker.time")
    def test_unhealthy(self, mock_time: MagicMock, mock_run: MagicMock):
        mock_run.return_value = MagicMock(stdout="unhealthy\n")
        mock_time.monotonic.side_effect = [0, 1, 2]
        assert health_check("mycontainer", timeout=10) is False

    @patch("rakkib.docker._run")
    @patch("rakkib.docker.container_running")
    @patch("rakkib.docker.time")
    def test_no_healthcheck_falls_back(self, mock_time: MagicMock, mock_running: MagicMock, mock_run: MagicMock):
        # docker inspect Health.Status returns empty when no healthcheck
        mock_run.return_value = MagicMock(stdout="")
        mock_running.return_value = True
        mock_time.monotonic.side_effect = [0, 1, 2]
        assert health_check("mycontainer", timeout=10) is True

    @patch("rakkib.docker._run")
    @patch("rakkib.docker.time")
    def test_timeout(self, mock_time: MagicMock, mock_run: MagicMock):
        mock_run.return_value = MagicMock(stdout="starting\n")
        mock_time.monotonic.side_effect = [0, 5, 10, 15]
        mock_time.sleep = MagicMock()
        assert health_check("mycontainer", timeout=5) is False

    @patch("rakkib.docker._run")
    @patch("rakkib.docker.container_running")
    @patch("rakkib.docker.time")
    def test_no_value_fallback(self, mock_time: MagicMock, mock_running: MagicMock, mock_run: MagicMock):
        mock_run.return_value = MagicMock(stdout="<no value>\n")
        mock_running.return_value = True
        mock_time.monotonic.side_effect = [0, 1, 2]
        assert health_check("mycontainer", timeout=10) is True

    @patch("rakkib.docker._run")
    @patch("rakkib.docker.container_running")
    @patch("rakkib.docker.time")
    def test_no_value_container_not_running(self, mock_time: MagicMock, mock_running: MagicMock, mock_run: MagicMock):
        mock_run.return_value = MagicMock(stdout="<no value>\n")
        mock_running.return_value = False
        mock_time.monotonic.side_effect = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        mock_time.sleep = MagicMock()
        assert health_check("mycontainer", timeout=10) is False

    @patch("rakkib.docker._run")
    @patch("rakkib.docker.time")
    def test_docker_error_during_inspect(self, mock_time: MagicMock, mock_run: MagicMock):
        mock_run.side_effect = [DockerError("oops", ["docker"], 1), MagicMock(stdout="healthy\n")]
        mock_time.monotonic.side_effect = [0, 1, 2, 3]
        mock_time.sleep = MagicMock()
        assert health_check("mycontainer", timeout=10) is True


class TestContainerRunning:
    @patch("rakkib.docker._run")
    def test_running(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(stdout="true\n")
        assert container_running("web") is True

    @patch("rakkib.docker._run")
    def test_not_running(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(stdout="false\n")
        assert container_running("web") is False

    @patch("rakkib.docker._run")
    def test_docker_error(self, mock_run: MagicMock):
        mock_run.side_effect = DockerError("oops", ["docker"], 1)
        assert container_running("web") is False


class TestContainerPublishesPort:
    @patch("rakkib.docker._run")
    def test_publishes_port(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(
            stdout='{"8080/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}'
        )
        assert container_publishes_port("web", 8080) is True

    @patch("rakkib.docker._run")
    def test_different_port(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(
            stdout='{"8080/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}'
        )
        assert container_publishes_port("web", 3000) is False

    @patch("rakkib.docker._run")
    def test_no_bindings(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(stdout='{"8080/tcp": null}')
        assert container_publishes_port("web", 8080) is False

    @patch("rakkib.docker._run")
    def test_docker_error(self, mock_run: MagicMock):
        mock_run.side_effect = DockerError("oops", ["docker"], 1)
        assert container_publishes_port("web", 8080) is False

    @patch("rakkib.docker._run")
    def test_empty_key(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(stdout='{"": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}')
        assert container_publishes_port("web", 8080) is False

    @patch("rakkib.docker._run")
    def test_json_decode_error(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(stdout="not-json")
        assert container_publishes_port("web", 8080) is False

    @patch("rakkib.docker._run")
    def test_value_error(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(stdout='{"abc/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}')
        assert container_publishes_port("web", 8080) is False


class TestNetworkExists:
    @patch("rakkib.docker._run")
    def test_exists(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=0)
        assert network_exists("mynet") is True

    @patch("rakkib.docker._run")
    def test_missing(self, mock_run: MagicMock):
        mock_run.side_effect = DockerError("oops", ["docker"], 1)
        assert network_exists("mynet") is False


class TestCreateNetwork:
    @patch("rakkib.docker.network_exists")
    @patch("rakkib.docker._run")
    def test_creates_when_missing(self, mock_run: MagicMock, mock_exists: MagicMock):
        mock_exists.return_value = False
        create_network("mynet")
        mock_run.assert_called_once_with(
            ["docker", "network", "create", "--driver", "bridge", "mynet"]
        )

    @patch("rakkib.docker.network_exists")
    @patch("rakkib.docker._run")
    def test_noop_when_exists(self, mock_run: MagicMock, mock_exists: MagicMock):
        mock_exists.return_value = True
        create_network("mynet")
        mock_run.assert_not_called()

    @patch("rakkib.docker.network_exists")
    @patch("rakkib.docker._run")
    def test_custom_driver(self, mock_run: MagicMock, mock_exists: MagicMock):
        mock_exists.return_value = False
        create_network("mynet", driver="overlay")
        mock_run.assert_called_once_with(
            ["docker", "network", "create", "--driver", "overlay", "mynet"]
        )


class TestRun:
    @patch("rakkib.docker.subprocess.run")
    def test_success_no_log(self, mock_subprocess: MagicMock):
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")
        from rakkib.docker import _run
        result = _run(["echo", "hello"])
        assert result.returncode == 0

    @patch("rakkib.docker.subprocess.run")
    def test_failure_raises(self, mock_subprocess: MagicMock):
        mock_subprocess.return_value = MagicMock(returncode=1, stderr="err")
        from rakkib.docker import _run
        with pytest.raises(DockerError) as exc_info:
            _run(["false"])
        assert exc_info.value.stderr == "err"
        assert exc_info.value.returncode == 1

    @patch("rakkib.docker.subprocess.run")
    def test_check_false_does_not_raise(self, mock_subprocess: MagicMock):
        mock_subprocess.return_value = MagicMock(returncode=1, stderr="err")
        from rakkib.docker import _run
        result = _run(["false"], check=False)
        assert result.returncode == 1

    @patch("rakkib.docker.subprocess.run")
    def test_log_redirect(self, mock_subprocess: MagicMock, tmp_path: Path):
        log = tmp_path / "out.log"
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")
        from rakkib.docker import _run
        _run(["echo", "hi"], log_path=log)
        assert log.exists()
        _, kwargs = mock_subprocess.call_args
        assert kwargs["stdout"] is not None
