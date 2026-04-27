"""Tests for Step 30 — Caddy."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from rakkib.state import State
from rakkib.steps import caddy


def _make_state(tmp_path: Path) -> State:
    return State(
        {
            "data_root": str(tmp_path),
            "docker_net": "caddy_net",
            "domain": "example.com",
        }
    )


def _subprocess_side_effect(network_exists: bool = False, caddy_running: bool = False):
    def side_effect(cmd, **kwargs):
        class Result:
            pass

        r = Result()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""

        if cmd[0:2] == ["docker", "network"] and cmd[2] == "inspect":
            r.returncode = 0 if network_exists else 1
        elif cmd[0:2] == ["docker", "network"] and cmd[2] == "create":
            r.returncode = 0
        elif cmd[0:4] == ["docker", "run", "--rm", "-v"]:
            r.returncode = 0
        elif cmd[0:3] == ["docker", "compose", "up"]:
            r.returncode = 0
        elif cmd[0:4] == ["docker", "compose", "exec", "caddy"]:
            r.returncode = 0
        elif cmd[0:3] == ["docker", "ps", "-q"]:
            r.stdout = "abc123" if caddy_running else ""
        else:
            r.returncode = 0
        return r

    return side_effect


def test_caddy_run_creates_network(tmp_path):
    state = _make_state(tmp_path)
    with patch("rakkib.steps.caddy.subprocess.run") as mock_run:
        mock_run.side_effect = _subprocess_side_effect(network_exists=False)
        caddy.run(state)

    create_calls = [c for c in mock_run.call_args_list if c[0][0][0:3] == ["docker", "network", "create"]]
    assert len(create_calls) == 1


def test_caddy_run_skips_existing_network(tmp_path):
    state = _make_state(tmp_path)
    with patch("rakkib.steps.caddy.subprocess.run") as mock_run:
        mock_run.side_effect = _subprocess_side_effect(network_exists=True)
        caddy.run(state)

    create_calls = [c for c in mock_run.call_args_list if c[0][0][0:3] == ["docker", "network", "create"]]
    assert len(create_calls) == 0


def test_caddy_run_renders_caddyfile(tmp_path):
    state = _make_state(tmp_path)
    with patch("rakkib.steps.caddy.subprocess.run") as mock_run:
        mock_run.side_effect = _subprocess_side_effect(network_exists=True)
        caddy.run(state)

    caddy_dir = tmp_path / "docker" / "caddy"
    assert (caddy_dir / "Caddyfile").exists()
    assert (caddy_dir / "Caddyfile.header").exists()
    assert (caddy_dir / "routes" / "root.caddy").exists()
    assert (caddy_dir / "Caddyfile.footer").exists()
    assert (caddy_dir / "docker-compose.yml").exists()


def test_caddy_run_backups_existing_caddyfile(tmp_path):
    state = _make_state(tmp_path)
    caddy_dir = tmp_path / "docker" / "caddy"
    caddy_dir.mkdir(parents=True)
    (caddy_dir / "Caddyfile").write_text("old")

    with patch("rakkib.steps.caddy.subprocess.run") as mock_run:
        mock_run.side_effect = _subprocess_side_effect(network_exists=True)
        caddy.run(state)

    assert (caddy_dir / "Caddyfile.bak").exists()
    assert (caddy_dir / "Caddyfile.bak").read_text() == "old"


def test_caddy_run_validates_before_promote(tmp_path):
    state = _make_state(tmp_path)
    validate_called = False

    def side_effect(cmd, **kwargs):
        nonlocal validate_called
        class Result:
            pass

        r = Result()
        r.stdout = ""
        r.stderr = ""
        if cmd[0:2] == ["docker", "run"] and cmd[2] == "--rm":
            validate_called = True
            r.returncode = 0
        else:
            r.returncode = 0
        return r

    with patch("rakkib.steps.caddy.subprocess.run") as mock_run:
        mock_run.side_effect = side_effect
        caddy.run(state)

    assert validate_called


def test_caddy_run_validation_failure(tmp_path):
    state = _make_state(tmp_path)

    def side_effect(cmd, **kwargs):
        class Result:
            pass

        r = Result()
        r.stdout = ""
        r.stderr = "bad config"
        if cmd[0:2] == ["docker", "run"] and cmd[2] == "--rm":
            r.returncode = 1
        else:
            r.returncode = 0
        return r

    with patch("rakkib.steps.caddy.subprocess.run") as mock_run:
        mock_run.side_effect = side_effect
        with pytest.raises(RuntimeError, match="Caddyfile validation failed"):
            caddy.run(state)


def test_caddy_run_reload_failure_restores_backup(tmp_path):
    state = _make_state(tmp_path)
    caddy_dir = tmp_path / "docker" / "caddy"
    caddy_dir.mkdir(parents=True)
    (caddy_dir / "Caddyfile").write_text("old")

    def side_effect(cmd, **kwargs):
        class Result:
            pass

        r = Result()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        if cmd[0:4] == ["docker", "compose", "exec", "caddy"]:
            r.returncode = 1
            r.stderr = "reload failed"
        elif cmd[0:3] == ["docker", "ps", "-q"]:
            r.stdout = "abc123"
        return r

    with patch("rakkib.steps.caddy.subprocess.run") as mock_run:
        mock_run.side_effect = side_effect
        with pytest.raises(RuntimeError, match="Caddy reload failed"):
            caddy.run(state)

    # Backup should have been restored
    assert (caddy_dir / "Caddyfile").read_text() == "old"


def test_caddy_verify_success(tmp_path):
    state = _make_state(tmp_path)

    def side_effect(cmd, **kwargs):
        class Result:
            pass

        r = Result()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        if cmd[0:2] == ["docker", "ps"]:
            r.stdout = "caddy"
        elif cmd[0:2] == ["curl", "-s"]:
            r.stdout = "OK"
        return r

    with patch("rakkib.steps.caddy.subprocess.run") as mock_run:
        mock_run.side_effect = side_effect
        result = caddy.verify(state)

    assert result.ok is True
    assert result.step == "caddy"


def test_caddy_verify_failure_container_missing(tmp_path):
    state = _make_state(tmp_path)

    def side_effect(cmd, **kwargs):
        class Result:
            pass

        r = Result()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    with patch("rakkib.steps.caddy.subprocess.run") as mock_run:
        mock_run.side_effect = side_effect
        result = caddy.verify(state)

    assert result.ok is False
    assert "not running" in result.message


def test_caddy_verify_failure_network_missing(tmp_path):
    state = _make_state(tmp_path)

    def side_effect(cmd, **kwargs):
        class Result:
            pass

        r = Result()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        if cmd[0:2] == ["docker", "ps"]:
            r.stdout = "caddy"
        elif cmd[0:2] == ["docker", "network"] and cmd[2] == "inspect":
            r.returncode = 1
        return r

    with patch("rakkib.steps.caddy.subprocess.run") as mock_run:
        mock_run.side_effect = side_effect
        result = caddy.verify(state)

    assert result.ok is False
    assert "network" in result.message.lower()


def test_caddy_verify_failure_health_check_failed(tmp_path):
    state = _make_state(tmp_path)

    def side_effect(cmd, **kwargs):
        class Result:
            pass

        r = Result()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        if cmd[0:2] == ["docker", "ps"]:
            r.stdout = "caddy"
        elif cmd[0:2] == ["curl", "-s"]:
            r.returncode = 1
            r.stdout = ""
        return r

    with patch("rakkib.steps.caddy.subprocess.run") as mock_run:
        mock_run.side_effect = side_effect
        result = caddy.verify(state)

    assert result.ok is False
    assert "health check failed" in result.message.lower()
