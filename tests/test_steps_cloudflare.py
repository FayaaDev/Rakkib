"""Tests for Step 3 — Cloudflare."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from rakkib.state import State
from rakkib.steps import cloudflare


def _make_state(tmp_path: Path, **overrides) -> State:
    defaults = {
        "data_root": str(tmp_path),
        "domain": "example.com",
        "docker_net": "caddy_net",
        "lan_ip": "127.0.0.1",
        "admin_user": "ubuntu",
        "cloudflare": {
            "auth_method": "browser_login",
            "tunnel_strategy": "new",
            "tunnel_name": "rakkib-example",
            "zone_in_cloudflare": True,
        },
        "cloudflared_metrics_port": "20241",
    }
    defaults.update(overrides)
    return State(defaults)


def _subprocess_side_effect(
    cloudflared_version: bool = True,
    tunnel_list_ok: bool = True,
    tunnel_info_ok: bool = True,
    tunnel_create_ok: bool = True,
    route_dns_ok: bool = True,
    route_dns_stderr: str = "",
    curl_ok: bool = True,
    container_running: bool = True,
    metrics_ok: bool = True,
    tunnels_json: list | None = None,
    tunnel_create_stderr: str = "",
):
    def side_effect(cmd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""

        bin_name = cmd[0]
        if isinstance(bin_name, str) and "cloudflared" in bin_name:
            sub = cmd[1] if len(cmd) > 1 else ""
            sub2 = cmd[2] if len(cmd) > 2 else ""
            if sub == "--version":
                r.returncode = 0 if cloudflared_version else 1
            elif sub == "tunnel" and sub2 == "list":
                r.returncode = 0 if tunnel_list_ok else 1
                if tunnels_json is not None:
                    r.stdout = json.dumps(tunnels_json)
                else:
                    r.stdout = json.dumps([{"name": "rakkib-example", "id": "test-uuid-123"}])
            elif sub == "tunnel" and sub2 == "info":
                r.returncode = 0 if tunnel_info_ok else 1
            elif sub == "tunnel" and sub2 == "create":
                r.returncode = 0 if tunnel_create_ok else 1
                r.stderr = tunnel_create_stderr
            elif sub == "tunnel" and sub2 == "route":
                r.returncode = 0 if route_dns_ok else 1
                r.stderr = route_dns_stderr
        elif bin_name == "curl":
            # metrics check uses curl
            if "metrics" in cmd[-1] if cmd else "":
                r.returncode = 0 if metrics_ok else 1
            else:
                r.returncode = 0 if curl_ok else 1
            r.stdout = '{"success":true}'
        elif bin_name == "docker":
            sub = cmd[1] if len(cmd) > 1 else ""
            if sub == "inspect":
                r.stdout = "true" if container_running else "false"
            elif sub == "ps":
                r.stdout = "cloudflared" if container_running else ""
        return r

    return side_effect


class TestRun:
    def test_run_rejects_missing_zone(self, tmp_path):
        state = _make_state(tmp_path, cloudflare={"zone_in_cloudflare": False})
        with pytest.raises(RuntimeError, match="not active in Cloudflare"):
            cloudflare.run(state)

    def test_run_rejects_missing_cloudflared(self, tmp_path):
        state = _make_state(tmp_path)
        with patch("rakkib.steps.cloudflare._run") as mock_run:
            mock_run.side_effect = RuntimeError("not found")
            with pytest.raises(RuntimeError, match="cloudflared CLI is not installed"):
                cloudflare.run(state)

    def test_run_browser_login_copies_cert(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        cert_path = cloudflared_dir / "cert.pem"
        default_cert = Path.home() / ".cloudflared" / "cert.pem"
        default_cert.parent.mkdir(parents=True, exist_ok=True)
        default_cert.write_text("cert-data")

        # Also need creds file to avoid the missing-credentials error
        (cloudflared_dir / "test-uuid-123.json").write_text("{}")

        with patch("rakkib.steps.cloudflare._run") as mock_run:
            with patch("rakkib.steps.cloudflare.subprocess.run") as mock_sub:
                with patch("shutil.copy2") as mock_copy:
                    mock_run.side_effect = _subprocess_side_effect()
                    mock_sub.return_value.returncode = 0
                    mock_sub.return_value.stdout = ""
                    mock_sub.return_value.stderr = ""
                    cloudflare.run(state)
                    mock_copy.assert_called_once()

    def test_run_new_tunnel_creates_and_discovers(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "new-uuid.json").write_text("{}")

        with patch("rakkib.steps.cloudflare._run") as mock_run:
            with patch("rakkib.steps.cloudflare.compose_up"):
                mock_run.side_effect = _subprocess_side_effect(
                    tunnels_json=[{"name": "rakkib-example", "id": "new-uuid"}]
                )
                cloudflare.run(state)

        assert state.get("cloudflare.tunnel_uuid") == "new-uuid"

    def test_run_existing_tunnel_uses_uuid(self, tmp_path):
        state = _make_state(
            tmp_path,
            cloudflare={
                "auth_method": "existing_tunnel",
                "tunnel_strategy": "existing",
                "tunnel_name": "rakkib-example",
                "zone_in_cloudflare": True,
                "tunnel_uuid": "existing-uuid-456",
            },
        )
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "existing-uuid-456.json").write_text("{}")

        with patch("rakkib.steps.cloudflare._run") as mock_run:
            with patch("rakkib.steps.cloudflare.compose_up"):
                mock_run.side_effect = _subprocess_side_effect()
                cloudflare.run(state)

        assert state.get("cloudflare.tunnel_uuid") == "existing-uuid-456"

    def test_run_renders_config_and_compose(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "test-uuid.json").write_text("{}")

        with patch("rakkib.steps.cloudflare._run") as mock_run:
            with patch("rakkib.steps.cloudflare.compose_up"):
                mock_run.side_effect = _subprocess_side_effect(
                    tunnels_json=[{"name": "rakkib-example", "id": "test-uuid"}]
                )
                cloudflare.run(state)

        cloudflared_dir = tmp_path / "data" / "cloudflared"
        docker_dir = tmp_path / "docker" / "cloudflared"
        assert (cloudflared_dir / "config.yml").exists()
        env_path = docker_dir / ".env"
        assert env_path.exists()
        env_text = env_path.read_text()
        assert "TUNNEL_UUID=test-uuid" in env_text
        assert "CLOUDFLARED_METRICS_PORT=20241" in env_text
        assert f"ADMIN_UID={state.get('admin_uid')}" in env_text
        assert f"ADMIN_GID={state.get('admin_gid')}" in env_text
        assert (docker_dir / "docker-compose.yml").exists()

    def test_run_api_token_verifies_and_sets_env(self, tmp_path):
        state = _make_state(
            tmp_path,
            cloudflare={
                "auth_method": "api_token",
                "tunnel_strategy": "new",
                "tunnel_name": "rakkib-example",
                "zone_in_cloudflare": True,
            },
        )
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "test-uuid-123.json").write_text("{}")

        with patch("rakkib.steps.cloudflare.getpass.getpass", return_value="my-token"):
            with patch("rakkib.steps.cloudflare.subprocess.run") as mock_sub:
                with patch("rakkib.steps.cloudflare._run") as mock_run:
                    with patch("rakkib.steps.cloudflare.compose_up"):
                        def curl_side(cmd, **kwargs):
                            r = MagicMock()
                            r.returncode = 0
                            r.stdout = '{"success":true}'
                            r.stderr = ""
                            return r
                        mock_sub.side_effect = curl_side
                        mock_run.side_effect = _subprocess_side_effect()
                        cloudflare.run(state)

    def test_run_existing_tunnel_repairs_auth(self, tmp_path):
        state = _make_state(
            tmp_path,
            cloudflare={
                "auth_method": "existing_tunnel",
                "tunnel_strategy": "existing",
                "tunnel_name": "rakkib-example",
                "zone_in_cloudflare": True,
                "tunnel_uuid": None,
                "tunnel_creds_host_path": None,
            },
        )
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "repaired-uuid.json").write_text("{}")

        with patch("rakkib.steps.cloudflare._run") as mock_run:
            with patch("rakkib.steps.cloudflare.compose_up"):
                with patch("rakkib.steps.cloudflare.subprocess.run") as mock_sub:
                    mock_sub.return_value.returncode = 0
                    mock_sub.return_value.stdout = ""
                    mock_sub.return_value.stderr = ""
                    mock_run.side_effect = _subprocess_side_effect(
                        tunnels_json=[{"name": "rakkib-example", "id": "repaired-uuid"}]
                    )
                    cloudflare.run(state)

        assert state.get("cloudflare.tunnel_uuid") == "repaired-uuid"

    def test_run_reuses_existing_tunnel_when_creds_found_in_admin_home(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "cert.pem").write_text("cert")
        reused_creds = tmp_path / "reused-uuid.json"
        reused_creds.write_text("{}")

        with patch("rakkib.steps.cloudflare._find_cloudflared_artifact") as mock_find:
            with patch("rakkib.steps.cloudflare._run") as mock_run:
                with patch("rakkib.steps.cloudflare.compose_up"):
                    mock_find.side_effect = lambda name, admin_user=None: reused_creds if name == "reused-uuid.json" else None
                    mock_run.side_effect = _subprocess_side_effect(
                        tunnels_json=[{"name": "rakkib-example", "id": "reused-uuid"}]
                    )
                    cloudflare.run(state)

        assert state.get("cloudflare.tunnel_uuid") == "reused-uuid"
        assert state.get("cloudflare.tunnel_name") == "rakkib-example"
        assert (tmp_path / "data" / "cloudflared" / "reused-uuid.json").exists()

    def test_run_creates_fresh_tunnel_when_existing_creds_are_missing(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "cert.pem").write_text("cert")

        def run_side_effect(cmd, **kwargs):
            if cmd[:4] == ["cloudflared", "tunnel", "list", "--output"]:
                result = MagicMock()
                result.returncode = 0
                result.stdout = json.dumps(
                    [
                        {"name": "rakkib-example", "id": "stale-uuid"},
                        {"name": "rakkib-example-1700000000", "id": "fresh-uuid"},
                    ]
                )
                result.stderr = ""
                return result
            if cmd[:3] == ["cloudflared", "--version"]:
                result = MagicMock()
                result.returncode = 0
                result.stdout = "cloudflared 1.0"
                result.stderr = ""
                return result
            if cmd[:3] == ["cloudflared", "tunnel", "list"]:
                result = MagicMock()
                result.returncode = 0
                result.stdout = json.dumps([{"name": "rakkib-example", "id": "stale-uuid"}])
                result.stderr = ""
                return result
            if cmd[:4] == ["cloudflared", "tunnel", "create", "rakkib-example"]:
                result = MagicMock()
                result.returncode = 1
                result.stdout = ""
                result.stderr = "tunnel with that name already exists"
                return result
            if cmd[:4] == ["cloudflared", "tunnel", "create", "rakkib-example-1700000000"]:
                result = MagicMock()
                result.returncode = 0
                result.stdout = ""
                result.stderr = "Tunnel credentials written to /root/.cloudflared/fresh-uuid.json"
                return result
            if cmd[:3] == ["cloudflared", "tunnel", "info"]:
                result = MagicMock()
                result.returncode = 0
                result.stdout = ""
                result.stderr = ""
                return result
            if cmd[:4] == ["cloudflared", "tunnel", "route", "dns"]:
                result = MagicMock()
                result.returncode = 0
                result.stdout = ""
                result.stderr = ""
                return result
            raise AssertionError(f"Unexpected command: {cmd}")

        fresh_creds = tmp_path / "root-cloudflared" / "fresh-uuid.json"
        fresh_creds.parent.mkdir(parents=True)
        fresh_creds.write_text("{}")

        with patch("rakkib.steps.cloudflare._cloudflared_bin", return_value="cloudflared"):
            with patch("rakkib.steps.cloudflare.time.time", return_value=1700000000):
                with patch("rakkib.steps.cloudflare._find_cloudflared_artifact") as mock_find:
                    with patch("rakkib.steps.cloudflare._run", side_effect=run_side_effect):
                        with patch("rakkib.steps.cloudflare.compose_up"):
                            mock_find.side_effect = lambda name, admin_user=None: fresh_creds if name == "fresh-uuid.json" else None
                            cloudflare.run(state)

        assert state.get("cloudflare.tunnel_uuid") == "fresh-uuid"
        assert state.get("cloudflare.tunnel_name") == "rakkib-example-1700000000"
        assert (tmp_path / "data" / "cloudflared" / "fresh-uuid.json").exists()

    def test_run_sets_credentials_permissions(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        creds_path = cloudflared_dir / "test-uuid-123.json"
        creds_path.write_text("{}")

        with patch("rakkib.steps.cloudflare._run") as mock_run:
            with patch("rakkib.steps.cloudflare.compose_up"):
                with patch("os.chmod") as mock_chmod:
                    mock_run.side_effect = _subprocess_side_effect()
                    cloudflare.run(state)
                    # os.chmod is called for cert.pem copy and creds json;
                    # assert the creds json got 0o600.
                    creds_chmod_calls = [
                        c for c in mock_chmod.call_args_list
                        if str(creds_path) in str(c[0][0])
                    ]
                    assert len(creds_chmod_calls) == 1
                    assert creds_chmod_calls[0][0][1] == 0o600

    def test_run_raises_on_dns_route_failure(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "test-uuid-123.json").write_text("{}")

        with patch("rakkib.steps.cloudflare._run") as mock_run:
            mock_run.side_effect = _subprocess_side_effect(route_dns_ok=False)
            with pytest.raises(RuntimeError, match="DNS route creation failed"):
                cloudflare.run(state)

    def test_run_accepts_existing_dns_route_errors(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "test-uuid-123.json").write_text("{}")

        with patch("rakkib.steps.cloudflare._run") as mock_run:
            with patch("rakkib.steps.cloudflare.compose_up"):
                mock_run.side_effect = _subprocess_side_effect(
                    route_dns_ok=False,
                    route_dns_stderr="record already exists for that hostname",
                )
                cloudflare.run(state)

    def test_run_raises_on_missing_credentials(self, tmp_path):
        state = _make_state(tmp_path)
        with patch("rakkib.steps.cloudflare._run") as mock_run:
            mock_run.side_effect = _subprocess_side_effect()
            with pytest.raises(RuntimeError, match="Tunnel credentials file not found"):
                cloudflare.run(state)


class TestVerify:
    def test_verify_success(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "cert.pem").write_text("cert")
        (cloudflared_dir / "config.yml").write_text("config")

        with patch("rakkib.steps.cloudflare.subprocess.run") as mock_run:
            with patch("rakkib.steps.cloudflare.container_running", return_value=True):
                mock_run.side_effect = _subprocess_side_effect()
                result = cloudflare.verify(state)

        assert result.ok is True
        assert result.step == "cloudflare"

    def test_verify_failure_no_cloudflared(self, tmp_path):
        state = _make_state(tmp_path)

        with patch("rakkib.steps.cloudflare.subprocess.run") as mock_run:
            mock_run.side_effect = _subprocess_side_effect(cloudflared_version=False)
            result = cloudflare.verify(state)

        assert result.ok is False
        assert "not installed" in result.message

    def test_verify_failure_no_data_dir(self, tmp_path):
        state = _make_state(tmp_path)

        with patch("rakkib.steps.cloudflare.subprocess.run") as mock_run:
            mock_run.side_effect = _subprocess_side_effect()
            result = cloudflare.verify(state)

        assert result.ok is False
        assert "does not exist" in result.message

    def test_verify_failure_no_cert(self, tmp_path):
        state = _make_state(
            tmp_path,
            cloudflare={
                "auth_method": "browser_login",
                "tunnel_strategy": "new",
                "tunnel_name": "rakkib-example",
                "zone_in_cloudflare": True,
            },
        )
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)

        with patch("rakkib.steps.cloudflare.subprocess.run") as mock_run:
            mock_run.side_effect = _subprocess_side_effect()
            result = cloudflare.verify(state)

        assert result.ok is False
        assert "cert.pem not found" in result.message

    def test_verify_failure_tunnel_list_fails(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "cert.pem").write_text("cert")

        with patch("rakkib.steps.cloudflare.subprocess.run") as mock_run:
            mock_run.side_effect = _subprocess_side_effect(tunnel_list_ok=False)
            result = cloudflare.verify(state)

        assert result.ok is False
        assert "tunnel list failed" in result.message

    def test_verify_failure_container_not_running(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "cert.pem").write_text("cert")
        (cloudflared_dir / "config.yml").write_text("config")

        with patch("rakkib.steps.cloudflare.subprocess.run") as mock_run:
            with patch("rakkib.steps.cloudflare.container_running", return_value=False):
                mock_run.side_effect = _subprocess_side_effect()
                result = cloudflare.verify(state)

        assert result.ok is False
        assert "not running" in result.message

    def test_verify_failure_metrics_endpoint(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "cert.pem").write_text("cert")
        (cloudflared_dir / "config.yml").write_text("config")

        with patch("rakkib.steps.cloudflare.subprocess.run") as mock_run:
            with patch("rakkib.steps.cloudflare.container_running", return_value=True):
                mock_run.side_effect = _subprocess_side_effect(metrics_ok=False)
                result = cloudflare.verify(state)

        assert result.ok is False
        assert "metrics endpoint failed" in result.message

    def test_verify_failure_missing_credentials(self, tmp_path):
        state = _make_state(
            tmp_path,
            cloudflare={
                "auth_method": "browser_login",
                "tunnel_strategy": "new",
                "tunnel_name": "rakkib-example",
                "zone_in_cloudflare": True,
                "tunnel_creds_host_path": "/nonexistent/creds.json",
            },
        )
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "cert.pem").write_text("cert")
        (cloudflared_dir / "config.yml").write_text("config")

        with patch("rakkib.steps.cloudflare.subprocess.run") as mock_run:
            with patch("rakkib.steps.cloudflare.container_running", return_value=True):
                mock_run.side_effect = _subprocess_side_effect()
                result = cloudflare.verify(state)

        assert result.ok is False
        assert "credentials not found" in result.message

    def test_verify_failure_tunnel_info_fails(self, tmp_path):
        state = _make_state(
            tmp_path,
            cloudflare={
                "auth_method": "browser_login",
                "tunnel_strategy": "new",
                "tunnel_name": "rakkib-example",
                "zone_in_cloudflare": True,
                "tunnel_uuid": "bad-uuid",
            },
        )
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "cert.pem").write_text("cert")
        (cloudflared_dir / "config.yml").write_text("config")

        with patch("rakkib.steps.cloudflare.subprocess.run") as mock_run:
            with patch("rakkib.steps.cloudflare.container_running", return_value=True):
                mock_run.side_effect = _subprocess_side_effect(tunnel_info_ok=False)
                result = cloudflare.verify(state)

        assert result.ok is False
        assert "tunnel info failed" in result.message


class TestGetTunnelUuid:
    def test_returns_uuid_when_match(self):
        with patch("rakkib.steps.cloudflare._run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([{"name": "my-tunnel", "id": "uuid-123"}]),
            )
            result = cloudflare._get_tunnel_uuid("my-tunnel")
        assert result == "uuid-123"

    def test_returns_none_when_no_match(self):
        with patch("rakkib.steps.cloudflare._run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([{"name": "other", "id": "uuid-456"}]),
            )
            result = cloudflare._get_tunnel_uuid("my-tunnel")
        assert result is None

    def test_returns_none_when_list_fails(self):
        with patch("rakkib.steps.cloudflare._run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = cloudflare._get_tunnel_uuid("my-tunnel")
        assert result is None

    def test_returns_none_on_json_decode_error(self):
        with patch("rakkib.steps.cloudflare._run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="not-json")
            result = cloudflare._get_tunnel_uuid("my-tunnel")
        assert result is None


class TestRunExistingTunnel:
    def test_run_existing_tunnel_with_valid_creds_skips_repair(self, tmp_path):
        state = _make_state(
            tmp_path,
            cloudflare={
                "auth_method": "existing_tunnel",
                "tunnel_strategy": "existing",
                "tunnel_name": "rakkib-example",
                "zone_in_cloudflare": True,
                "tunnel_uuid": "existing-uuid-456",
                "tunnel_creds_host_path": str(tmp_path / "data" / "cloudflared" / "existing-uuid-456.json"),
            },
        )
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "existing-uuid-456.json").write_text("{}")

        with patch("rakkib.steps.cloudflare._run") as mock_run:
            with patch("rakkib.steps.cloudflare.compose_up"):
                mock_run.side_effect = _subprocess_side_effect()
                cloudflare.run(state)

        assert state.get("cloudflare.tunnel_uuid") == "existing-uuid-456"

    def test_run_compose_up_docker_error(self, tmp_path):
        state = _make_state(tmp_path)
        cloudflared_dir = tmp_path / "data" / "cloudflared"
        cloudflared_dir.mkdir(parents=True)
        (cloudflared_dir / "test-uuid-123.json").write_text("{}")

        from rakkib.docker import DockerError
        with patch("rakkib.steps.cloudflare._run") as mock_run:
            with patch("rakkib.steps.cloudflare.compose_up") as mock_compose:
                mock_run.side_effect = _subprocess_side_effect()
                mock_compose.side_effect = DockerError("boom", ["docker"], 1, "compose failed")
                with pytest.raises(RuntimeError, match="docker compose up failed"):
                    cloudflare.run(state)
