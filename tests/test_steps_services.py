"""Tests for rakkib.steps.services."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from rakkib.hooks import services as service_hooks
from rakkib.state import State
from rakkib.steps import selected_service_defs
from rakkib.steps import VerificationResult
from rakkib.steps import services as services_step


@pytest.fixture
def fake_repo(tmp_path: Path):
    """Create a minimal repo structure with registry and templates."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Registry
    registry = {
        "services": [
            {"id": "postgres", "depends_on": [], "host_service": False, "default_port": 5432},
            {"id": "nocodb", "depends_on": ["postgres"], "host_service": False, "default_port": 8080},
            {"id": "homepage", "depends_on": [], "host_service": False, "default_port": 3000},
            {"id": "openclaw", "depends_on": [], "host_service": True, "default_port": 18789},
        ]
    }
    (repo / "registry.yaml").write_text(yaml.dump(registry))

    # Templates
    for svc in ["postgres", "nocodb", "homepage"]:
        tmpl_dir = repo / "templates" / "docker" / svc
        tmpl_dir.mkdir(parents=True)
        (tmpl_dir / "docker-compose.yml.tmpl").write_text(f"# {svc} compose\n")
        (tmpl_dir / ".env.example").write_text(f"{svc.upper()}_VAR={{VALUE}}\n")

    uptime_kuma_dir = repo / "templates" / "docker" / "uptime-kuma"
    uptime_kuma_dir.mkdir(parents=True)
    (uptime_kuma_dir / "sync-monitors.cjs.tmpl").write_text("console.log('sync');\n")

    # Caddy routes
    caddy_dir = repo / "templates" / "caddy" / "routes"
    caddy_dir.mkdir(parents=True)
    for svc in ["nocodb", "homepage"]:
        (caddy_dir / f"{svc}.caddy.tmpl").write_text(f"# {svc} route\n")

    return repo


class TestSelectedServiceDefs:
    def test_dependency_order(self, fake_repo: Path):
        state = State({
            "foundation_services": ["nocodb", "homepage"],
            "selected_services": ["homepage"],
        })
        registry = services_step._load_registry()
        defs = selected_service_defs(state, registry)
        ids = [d["id"] for d in defs]
        assert ids == ["homepage", "nocodb"]

    def test_skips_unselected(self, fake_repo: Path):
        state = State({"foundation_services": ["nocodb"]})
        registry = services_step._load_registry()
        defs = selected_service_defs(state, registry)
        ids = [d["id"] for d in defs]
        assert "homepage" not in ids


class TestGenerateMissingSecrets:
    def test_generates_postgres_password(self):
        state = State({})
        services_step._generate_missing_secrets(state)
        assert state.get("POSTGRES_PASSWORD") is not None
        assert len(state.get("POSTGRES_PASSWORD")) >= 16

    def test_preserves_existing_secret(self):
        state = State({"POSTGRES_PASSWORD": "keepme"})
        services_step._generate_missing_secrets(state)
        assert state.get("POSTGRES_PASSWORD") == "keepme"

    def test_generates_nocodb_secrets(self):
        state = State({"foundation_services": ["nocodb"]})
        services_step._generate_missing_secrets(state)
        assert state.get("NOCODB_ADMIN_PASS") is not None
        assert state.get("NOCODB_DB_PASS") is not None

    def test_generates_n8n_encryption_when_fresh(self):
        state = State({
            "selected_services": ["n8n"],
            "secrets": {"n8n_mode": "fresh"},
        })
        services_step._generate_missing_secrets(state)
        assert state.get("N8N_ENCRYPTION_KEY") is not None

    def test_does_not_generate_n8n_encryption_when_migrate(self):
        state = State({
            "selected_services": ["n8n"],
            "secrets": {"n8n_mode": "migrate"},
        })
        services_step._generate_missing_secrets(state)
        assert state.get("N8N_ENCRYPTION_KEY") is None

    def test_prefers_secrets_values_over_generation(self):
        """When secrets.values already has a password (set by Step 4),
        Step 5 must reuse it instead of generating a divergent one."""
        state = State({
            "foundation_services": ["nocodb"],
            "selected_services": ["n8n"],
            "secrets": {
                "n8n_mode": "fresh",
                "values": {
                    "NOCODB_DB_PASS": "from-step4-nocodb",
                    "N8N_DB_PASS": "from-step4-n8n",
                },
            },
        })
        services_step._generate_missing_secrets(state)
        assert state.get("NOCODB_DB_PASS") == "from-step4-nocodb"
        assert state.get("N8N_DB_PASS") == "from-step4-n8n"

    def test_generates_when_secrets_values_empty(self):
        """When secrets.values has no entry, Step 5 should still generate."""
        state = State({
            "foundation_services": ["nocodb"],
            "secrets": {"values": {}},
        })
        services_step._generate_missing_secrets(state)
        assert state.get("NOCODB_DB_PASS") is not None
        assert len(state.get("NOCODB_DB_PASS")) > 0


class TestRenderEnvExample:
    def test_renders_and_sets_perms(self, tmp_path: Path):
        state = State({"VALUE": "hello"})
        tmpl = tmp_path / "env.tmpl"
        tmpl.write_text("VAR={{VALUE}}")
        dst = tmp_path / ".env"
        services_step._render_env_example(state, tmpl, dst)
        assert dst.exists()
        assert "hello" in dst.read_text()
        assert oct(dst.stat().st_mode)[-3:] == "600"

    def test_preserves_existing_keys(self, tmp_path: Path):
        state = State({"KEEP": "new_val"})
        existing_env = tmp_path / ".env"
        existing_env.write_text("KEEP=old_val\nOTHER=stuff\n")
        tmpl = tmp_path / "env.tmpl"
        tmpl.write_text("KEEP={{KEEP}}\nOTHER={{OTHER}}")
        services_step._render_env_example(state, tmpl, existing_env, preserve_keys=["KEEP"])
        content = existing_env.read_text()
        assert "old_val" in content


class TestRun:
    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.compose_up")
    @patch("rakkib.steps.services._reload_caddy")
    def test_deploys_selected_services(
        self,
        mock_reload: MagicMock,
        mock_compose: MagicMock,
        mock_repo: MagicMock,
        fake_repo: Path,
        tmp_path: Path,
    ):
        mock_repo.return_value = fake_repo
        data_root = tmp_path / "srv"
        state = State({
            "foundation_services": ["nocodb"],
            "selected_services": [],
            "data_root": str(data_root),
            "backup_dir": str(data_root / "backups"),
        })
        services_step.run(state)

        mock_compose.assert_called_once()
        args, kwargs = mock_compose.call_args
        assert "nocodb" in str(args[0])
        mock_reload.assert_called_once()

    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.compose_up")
    @patch("rakkib.steps.services._reload_caddy")
    @patch("rakkib.steps.services._run_named_hooks")
    def test_skips_host_service(
        self,
        mock_hooks: MagicMock,
        mock_reload: MagicMock,
        mock_compose: MagicMock,
        mock_repo: MagicMock,
        fake_repo: Path,
        tmp_path: Path,
    ):
        mock_repo.return_value = fake_repo
        data_root = tmp_path / "srv"
        state = State({
            "foundation_services": [],
            "selected_services": ["openclaw"],
            "data_root": str(data_root),
            "backup_dir": str(data_root / "backups"),
        })
        services_step.run(state)
        mock_compose.assert_not_called()
        assert mock_hooks.call_count == 3
        assert mock_hooks.call_args_list[0].args[0] == []
        assert mock_hooks.call_args_list[1].args[0] == []
        assert mock_hooks.call_args_list[2].args[0] == []

    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.compose_up")
    @patch("rakkib.steps.services._reload_caddy")
    def test_renders_env_from_example(
        self,
        mock_reload: MagicMock,
        mock_compose: MagicMock,
        mock_repo: MagicMock,
        fake_repo: Path,
        tmp_path: Path,
    ):
        mock_repo.return_value = fake_repo
        data_root = tmp_path / "srv"
        state = State({
            "foundation_services": ["nocodb"],
            "selected_services": [],
            "data_root": str(data_root),
            "backup_dir": str(data_root / "backups"),
            "VALUE": "test123",
        })
        services_step.run(state)
        env_path = data_root / "docker" / "nocodb" / ".env"
        assert env_path.exists()

    @patch("rakkib.steps.services.compose_up")
    @patch("rakkib.steps.services._reload_caddy")
    @patch("rakkib.steps.services._run_named_hooks")
    @patch("rakkib.hooks.services.container_running", return_value=False)
    def test_all_registry_services_render_for_add_sync(
        self,
        _mock_hook_container_running: MagicMock,
        mock_hooks: MagicMock,
        mock_reload: MagicMock,
        mock_compose: MagicMock,
        tmp_path: Path,
    ):
        data_root = tmp_path / "srv"
        state = State(
            {
                "data_root": str(data_root),
                "domain": "example.com",
                "docker_net": "caddy_net",
                "platform": "linux",
                "host_gateway": "172.18.0.1",
                "foundation_services": ["nocodb", "homepage", "uptime-kuma", "dockge"],
                "selected_services": ["n8n", "immich", "transfer", "jellyfin", "openclaw"],
                "subdomains": {
                    "nocodb": "data",
                    "homepage": "home",
                    "uptime-kuma": "status",
                    "dockge": "dock",
                    "n8n": "flow",
                    "immich": "photos",
                    "transfer": "send",
                    "jellyfin": "media",
                    "openclaw": "claw",
                },
                "NOCODB_SUBDOMAIN": "data",
                "HOMEPAGE_SUBDOMAIN": "home",
                "UPTIME_KUMA_SUBDOMAIN": "status",
                "DOCKGE_SUBDOMAIN": "dock",
                "N8N_SUBDOMAIN": "flow",
                "IMMICH_SUBDOMAIN": "photos",
                "TRANSFER_SUBDOMAIN": "send",
                "JELLYFIN_SUBDOMAIN": "media",
                "OPENCLAW_SUBDOMAIN": "claw",
                "NOCODB_DB_PASS": "nocodb-pass",
                "NOCODB_ADMIN_PASS": "nocodb-admin-pass",
                "ADMIN_EMAIL": "admin@example.com",
                "UPTIME_KUMA_ADMIN_USER": "admin",
                "UPTIME_KUMA_ADMIN_PASS": "uptime-pass",
                "N8N_DB_PASS": "n8n-pass",
                "N8N_ENCRYPTION_KEY": "n8n-encryption-key-123456789012",
                "IMMICH_DB_PASSWORD": "immich-password",
                "IMMICH_VERSION": "release",
                "TZ": "Asia/Riyadh",
                "secrets": {
                    "values": {
                        "NOCODB_DB_PASS": "nocodb-pass",
                        "N8N_DB_PASS": "n8n-pass",
                    }
                },
            }
        )

        services_step.run(state)

        composed = {Path(call.args[0]).name for call in mock_compose.call_args_list}
        assert composed == {"dockge", "homepage", "immich", "jellyfin", "n8n", "nocodb", "transfer", "uptime-kuma"}
        mock_reload.assert_called_once()
        assert any(call.args[3]["id"] == "openclaw" for call in mock_hooks.call_args_list)

        routes = {path.name for path in (data_root / "docker" / "caddy" / "routes").glob("*.caddy")}
        assert routes == {
            "dockge.caddy",
            "homepage.caddy",
            "immich.caddy",
            "jellyfin.caddy",
            "n8n.caddy",
            "nocodb.caddy",
            "openclaw.caddy",
            "transfer.caddy",
            "uptime-kuma.caddy",
        }

        generated_files = [path for path in data_root.rglob("*") if path.is_file()]
        unresolved = [
            str(path.relative_to(data_root))
            for path in generated_files
            if "{{" in path.read_text(errors="ignore") or "}}" in path.read_text(errors="ignore")
        ]
        assert unresolved == []


class TestRunSingleService:
    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.compose_up")
    @patch("rakkib.steps.services._reload_caddy")
    def test_deploys_single_service(self, mock_reload, mock_compose, mock_repo, fake_repo, tmp_path):
        mock_repo.return_value = fake_repo
        data_root = tmp_path / "srv"
        state = State({
            "foundation_services": [],
            "selected_services": [],
            "data_root": str(data_root),
            "backup_dir": str(data_root / "backups"),
        })
        services_step.run_single_service(state, "nocodb")
        mock_compose.assert_called_once()
        mock_reload.assert_called_once()

    @patch("rakkib.steps.services.compose_up")
    @patch("rakkib.steps.services._reload_caddy")
    @patch("rakkib.steps.services.sync_shared_artifacts")
    def test_deploys_immich_single_service(self, mock_sync, mock_reload, mock_compose, tmp_path):
        data_root = tmp_path / "srv"
        state = State(
            {
                "data_root": str(data_root),
                "domain": "example.com",
                "docker_net": "caddy_net",
                "selected_services": ["immich"],
                "subdomains": {"immich": "photos"},
                "IMMICH_SUBDOMAIN": "photos",
                "IMMICH_DB_PASSWORD": "immich-password",
                "IMMICH_VERSION": "release",
                "TZ": "Asia/Riyadh",
            }
        )

        services_step.run_single_service(state, "immich")

        env_path = data_root / "docker" / "immich" / ".env"
        compose_path = data_root / "docker" / "immich" / "docker-compose.yml"
        assert env_path.exists()
        assert "UPLOAD_LOCATION=" in env_path.read_text()
        assert "DB_PASSWORD=immich-password" in env_path.read_text()
        assert compose_path.exists()
        mock_compose.assert_called_once()
        assert Path(mock_compose.call_args.args[0]).name == "immich"
        mock_reload.assert_called_once()
        mock_sync.assert_called_once()

    @patch("rakkib.steps.services._repo_dir")
    def test_raises_for_unknown_service(self, mock_repo, fake_repo, tmp_path):
        mock_repo.return_value = fake_repo
        state = State({
            "foundation_services": [],
            "selected_services": [],
            "data_root": str(tmp_path / "srv"),
            "backup_dir": str(tmp_path / "srv" / "backups"),
        })
        with pytest.raises(ValueError, match="not found in registry"):
            services_step.run_single_service(state, "unknown")


class TestSpecialHandlers:
    @patch("rakkib.hooks.services.subprocess.run")
    @patch("rakkib.hooks.services.os.geteuid", return_value=1000)
    def test_run_as_user_injects_package_manager_safe_env(self, _mock_euid, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        service_hooks._run_as_user(
            "admin",
            Path("/home/admin"),
            1000,
            ["true"],
            extra_env={"OPENCLAW_NO_PROMPT": "1"},
        )

        env = mock_run.call_args.kwargs["env"]
        assert env["DEBIAN_FRONTEND"] == "noninteractive"
        assert env["APT_LISTCHANGES_FRONTEND"] == "none"
        assert env["NEEDRESTART_MODE"] == "a"
        assert env["NEEDRESTART_SUSPEND"] == "1"
        assert env["UCF_FORCE_CONFFOLD"] == "1"
        assert env["OPENCLAW_NO_PROMPT"] == "1"

    @patch("rakkib.hooks.services.subprocess.run")
    @patch("rakkib.hooks.services.os.geteuid", return_value=0)
    def test_run_as_user_preserves_safe_env_when_using_sudo(self, _mock_euid, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        service_hooks._run_as_user("admin", Path("/home/admin"), 1000, ["true"])

        run_cmd = mock_run.call_args.args[0]
        assert run_cmd[:5] == ["sudo", "-n", "-u", "admin", "-H"]
        assert "DEBIAN_FRONTEND=noninteractive" in run_cmd
        assert "NEEDRESTART_MODE=a" in run_cmd
        assert "NEEDRESTART_SUSPEND=1" in run_cmd

    @patch("rakkib.hooks.services._run_as_service_user")
    @patch("rakkib.hooks.services.shutil.which", return_value=None)
    def test_resolve_openclaw_bin_uses_service_user_shell(self, _mock_which, mock_run_as_user):
        mock_run_as_user.return_value = MagicMock(returncode=0, stdout="/home/admin/.local/bin/openclaw\n")

        resolved = service_hooks._resolve_openclaw_bin(State({"admin_user": "admin"}))

        assert resolved == Path("/home/admin/.local/bin/openclaw")

    @patch("rakkib.hooks.services._run_openclaw")
    @patch("rakkib.hooks.services._resolve_openclaw_bin")
    @patch("rakkib.hooks.services._run_as_service_user")
    @patch("rakkib.hooks.services.wait_for_apt_locks", return_value=None)
    @patch("rakkib.hooks.services.shutil.which", return_value="/usr/bin/curl")
    def test_openclaw_install_installs_without_onboard_then_uses_absolute_path(
        self,
        _mock_curl,
        mock_wait_for_locks,
        mock_run_as_user,
        mock_resolve_bin,
        mock_run_openclaw,
    ):
        mock_resolve_bin.side_effect = [None, Path("/home/admin/.local/bin/openclaw")]
        mock_run_as_user.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_run_openclaw.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        state = State({"admin_user": "admin"})

        with patch("pathlib.Path.exists", return_value=False), patch("rakkib.hooks.services.os.geteuid", return_value=1000):
            service_hooks.openclaw_install(state, {}, Path("."), Path("."), Path("hook.log"), {})

        install_cmd = mock_run_as_user.call_args_list[0].args[1]
        assert install_cmd[-1] == "curl -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard --no-prompt"
        assert mock_run_as_user.call_args_list[0].kwargs["extra_env"] == {"OPENCLAW_NO_PROMPT": "1"}
        mock_wait_for_locks.assert_called_once()
        first_call = mock_run_openclaw.call_args_list[0].args
        second_call = mock_run_openclaw.call_args_list[1].args
        assert first_call[0] == state
        assert first_call[1] == Path("/home/admin/.local/bin/openclaw")
        assert first_call[2] == ["--version"]
        assert second_call[0] == state
        assert second_call[1] == Path("/home/admin/.local/bin/openclaw")
        assert second_call[2][0] == "onboard"

    @patch("rakkib.hooks.services.wait_for_apt_locks", return_value="Timed out waiting for apt/dpkg locks: /var/lib/dpkg/lock-frontend. unattended-upgrades is running.")
    @patch("rakkib.hooks.services.shutil.which", side_effect=lambda cmd: "/usr/bin/apt-get" if cmd == "apt-get" else "/usr/bin/curl")
    def test_openclaw_install_fails_actionably_when_apt_lock_wait_times_out(self, _mock_which, _mock_wait):
        state = State({"admin_user": "admin"})

        with patch("rakkib.hooks.services.os.geteuid", return_value=1000):
            with pytest.raises(RuntimeError, match="unattended-upgrades"):
                service_hooks.openclaw_install(state, {}, Path("."), Path("."), Path("hook.log"), {})

    @patch("rakkib.hooks.services._service_admin_user", return_value=("admin", Path("/home/admin"), 1000))
    @patch("rakkib.hooks.services.subprocess.run", side_effect=subprocess.TimeoutExpired(["openclaw", "gateway", "restart"], 1))
    def test_openclaw_command_timeout_is_actionable(self, _mock_run, _mock_user):
        with pytest.raises(RuntimeError, match="timed out"):
            service_hooks._run_openclaw(State({"admin_user": "admin"}), Path("/home/admin/.local/bin/openclaw"), ["gateway", "restart"], check=False)

    @patch("rakkib.hooks.services._run_openclaw")
    @patch("rakkib.hooks.services.wait_for_apt_locks", return_value=None)
    def test_openclaw_install_updates_bind_when_config_exists(self, _mock_wait, mock_run_openclaw):
        mock_run_openclaw.side_effect = [
            MagicMock(returncode=0, stdout="2026.4.26", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        state = State(
            {
                "admin_user": "admin",
                "domain": "rakkib.app",
                "subdomains": {"openclaw": "claw"},
                "foundation_services": ["homepage"],
            }
        )

        with patch("rakkib.hooks.services._resolve_openclaw_bin", return_value=Path("/home/admin/.local/bin/openclaw")), patch(
            "pathlib.Path.exists", return_value=True
        ), patch("rakkib.hooks.services.os.geteuid", return_value=1000):
            service_hooks.openclaw_install(state, {}, Path("."), Path("."), Path("hook.log"), {})

        assert mock_run_openclaw.call_args_list[1].args[2] == ["config", "set", "gateway.bind", "lan"]
        assert mock_run_openclaw.call_args_list[2].args[2] == [
            "config",
            "set",
            "gateway.controlUi.allowedOrigins",
            json.dumps(service_hooks._openclaw_allowed_origins(state)),
        ]

    @patch("rakkib.hooks.services._run_openclaw")
    @patch("rakkib.hooks.services.subprocess.run")
    @patch("rakkib.hooks.services.wait_for_apt_locks", return_value=None)
    def test_openclaw_install_tolerates_nonzero_onboard_when_artifacts_exist(self, _mock_wait, _mock_subprocess, mock_run_openclaw):
        mock_run_openclaw.side_effect = [
            MagicMock(returncode=0, stdout="2026.4.26", stderr=""),
            MagicMock(returncode=1, stdout="Updated ~/.openclaw/openclaw.json", stderr="daemon warning"),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        state = State({"admin_user": "root", "foundation_services": []})
        config_path = Path("/root/.openclaw/openclaw.json")
        service_path = Path("/root/.config/systemd/user/openclaw-gateway.service")
        config_checks = {"count": 0}

        def fake_exists(path_obj: Path) -> bool:
            if path_obj == config_path:
                config_checks["count"] += 1
                return config_checks["count"] > 1
            return path_obj == service_path

        with patch("rakkib.hooks.services._resolve_openclaw_bin", return_value=Path("/root/.local/bin/openclaw")), patch(
            "rakkib.hooks.services._service_admin_user", return_value=("root", Path("/root"), 0)
        ), patch("pathlib.Path.exists", side_effect=fake_exists), patch("rakkib.hooks.services.os.geteuid", return_value=0):
            service_hooks.openclaw_install(state, {}, Path("."), Path("."), Path("hook.log"), {})

        assert mock_run_openclaw.call_args_list[1].args[2][0] == "onboard"
        assert mock_run_openclaw.call_args_list[2].args[2] == ["config", "set", "gateway.bind", "lan"]

    @patch("rakkib.hooks.services._run_openclaw")
    @patch("rakkib.hooks.services.subprocess.run")
    @patch("rakkib.hooks.services.wait_for_apt_locks", return_value=None)
    def test_openclaw_install_raises_with_stderr_when_onboard_fails_without_artifacts(self, _mock_wait, _mock_subprocess, mock_run_openclaw):
        mock_run_openclaw.side_effect = [
            MagicMock(returncode=0, stdout="2026.4.26", stderr=""),
            MagicMock(returncode=1, stdout="Updated ~/.openclaw/openclaw.json", stderr="failed to reach systemd user bus"),
        ]
        state = State({"admin_user": "root", "foundation_services": []})

        with patch("rakkib.hooks.services._resolve_openclaw_bin", return_value=Path("/root/.local/bin/openclaw")), patch(
            "rakkib.hooks.services._service_admin_user", return_value=("root", Path("/root"), 0)
        ), patch("pathlib.Path.exists", return_value=False), patch("rakkib.hooks.services.os.geteuid", return_value=0):
            with pytest.raises(RuntimeError, match="failed to reach systemd user bus"):
                service_hooks.openclaw_install(state, {}, Path("."), Path("."), Path("hook.log"), {})

    def test_openclaw_paths_follow_admin_home(self):
        config_path, service_path = service_hooks._openclaw_paths(Path("/root"))
        assert config_path == Path("/root/.openclaw/openclaw.json")
        assert service_path == Path("/root/.config/systemd/user/openclaw-gateway.service")

    def test_openclaw_allowed_origins_include_public_and_local(self):
        state = State({"domain": "rakkib.app", "subdomains": {"openclaw": "claw"}})
        assert service_hooks._openclaw_allowed_origins(state) == [
            "https://claw.rakkib.app",
            "http://claw.rakkib.app",
            "http://127.0.0.1:18789",
            "http://localhost:18789",
        ]

    @patch("rakkib.hooks.services._run_as_user")
    @patch("rakkib.hooks.services._resolve_openclaw_bin_for_user")
    def test_migrate_root_openclaw_service_stops_and_uninstalls_root_service(self, mock_resolve_bin, mock_run_as_user):
        mock_resolve_bin.return_value = Path("/root/.local/bin/openclaw")
        mock_run_as_user.return_value = MagicMock(returncode=0, stdout="", stderr="")
        state = State({"admin_user": "ubuntu"})

        with patch("pathlib.Path.exists", side_effect=lambda _self: True):
            service_hooks._migrate_root_openclaw_service(state)

        assert mock_run_as_user.call_args_list[0].args[3] == ["/root/.local/bin/openclaw", "gateway", "stop"]
        assert mock_run_as_user.call_args_list[1].args[3] == ["/root/.local/bin/openclaw", "gateway", "uninstall"]

    def test_homepage_hook_writes_services_yaml(self, tmp_path):
        state = State(
            {
                "foundation_services": ["nocodb", "homepage"],
                "selected_services": ["n8n"],
                "domain": "example.com",
                "subdomains": {"nocodb": "data", "n8n": "flow"},
            }
        )
        registry = services_step._load_registry()
        service_hooks.homepage_services_yaml(state, {}, tmp_path, tmp_path, tmp_path / "hook.log", registry)
        content = (tmp_path / "data" / "homepage" / "config" / "services.yaml").read_text()
        assert "NocoDB" in content
        assert "https://data.example.com" in content
        assert "n8n" in content

    def test_render_extra_templates(self, fake_repo, tmp_path):
        tmpl = fake_repo / "templates" / "docker" / "n8n" / "n8n.env.tmpl"
        tmpl.parent.mkdir(parents=True, exist_ok=True)
        tmpl.write_text("# n8n config")
        state = State({})
        svc = {
            "extra_templates": [
                {
                    "src": "templates/docker/n8n/n8n.env.tmpl",
                    "dst": "docker/n8n/n8n.env",
                }
            ]
        }
        services_step._render_extra_templates(state, svc, fake_repo, tmp_path)
        assert (tmp_path / "docker" / "n8n" / "n8n.env").exists()

    @patch("rakkib.hooks.services.subprocess.run")
    @patch("rakkib.hooks.services.container_running", return_value=True)
    def test_sync_shared_artifacts_writes_kuma_monitors(self, _mock_running, mock_run, fake_repo, tmp_path):
        state = State(
            {
                "foundation_services": ["homepage", "uptime-kuma", "nocodb"],
                "selected_services": ["n8n"],
                "domain": "example.com",
                "data_root": str(tmp_path),
                "subdomains": {
                    "homepage": "home",
                    "uptime-kuma": "status",
                    "nocodb": "data",
                    "n8n": "flow",
                },
                "UPTIME_KUMA_ADMIN_USER": "admin",
                "UPTIME_KUMA_ADMIN_PASS": "secret-pass",
            }
        )
        registry = services_step._load_registry()

        service_hooks.sync_shared_artifacts(state, fake_repo, tmp_path, registry)

        payload = json.loads((tmp_path / "data" / "uptime-kuma" / "rakkib-monitors.json").read_text())
        assert payload["admin"]["username"] == "admin"
        assert payload["admin"]["password"] == "secret-pass"
        service_ids = {monitor["service_id"] for monitor in payload["monitors"]}
        assert "nocodb" in service_ids
        assert "n8n" in service_ids
        sync_script = tmp_path / "data" / "uptime-kuma" / "sync-monitors.cjs"
        assert sync_script.exists()
        assert any("uptime-kuma" in str(call.args[0]) for call in mock_run.call_args_list)

    @patch("rakkib.hooks.services.subprocess.run")
    def test_service_postgres_login_preflight_uses_service_contract(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        state = State({"secrets": {"values": {"N8N_DB_PASS": "db-pass"}}})
        svc = {"id": "n8n", "postgres": {"role": "n8n", "db": "n8n_db", "password_key": "N8N_DB_PASS"}}

        service_hooks.service_postgres_login_preflight(state, svc, Path("."), Path("."), Path("hook.log"), {})

        mock_run.assert_called_once_with(
            [
                "docker",
                "exec",
                "-e",
                "PGPASSWORD=db-pass",
                "postgres",
                "psql",
                "-h",
                "127.0.0.1",
                "-U",
                "n8n",
                "-d",
                "n8n_db",
                "-c",
                "select 1;",
            ],
            capture_output=True,
            text=True,
        )

    def test_service_postgres_login_preflight_raises_when_password_missing(self):
        state = State({"secrets": {"values": {}}})
        svc = {"id": "n8n", "postgres": {"role": "n8n", "password_key": "N8N_DB_PASS"}}

        with pytest.raises(RuntimeError, match="N8N_DB_PASS"):
            service_hooks.service_postgres_login_preflight(state, svc, Path("."), Path("."), Path("hook.log"), {})

    @patch("rakkib.hooks.services.subprocess.run")
    def test_service_postgres_login_preflight_raises_on_failed_login(self, mock_run):
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="password authentication failed")
        state = State({"N8N_DB_PASS": "bad-pass"})
        svc = {"id": "n8n", "postgres": {"role": "n8n", "password_key": "N8N_DB_PASS"}}

        with pytest.raises(RuntimeError, match="service 'n8n'"):
            service_hooks.service_postgres_login_preflight(state, svc, Path("."), Path("."), Path("hook.log"), {})


class TestRemoveSingleService:
    @patch("rakkib.steps.services.compose_down")
    @patch("rakkib.steps.services.subprocess.run")
    def test_full_purge_removes_files_and_drops_postgres_resources(self, mock_run, mock_down, tmp_path):
        data_root = tmp_path / "srv"
        service_dir = data_root / "docker" / "n8n"
        service_dir.mkdir(parents=True)
        (service_dir / "docker-compose.yml").write_text("services: {}\n")

        route_path = data_root / "docker" / "caddy" / "routes"
        route_path.mkdir(parents=True)
        (route_path / "n8n.caddy").write_text("route\n")

        data_dir = data_root / "data" / "n8n"
        data_dir.mkdir(parents=True)
        (data_dir / "payload.txt").write_text("payload\n")

        extra_path = data_root / "docker" / "n8n" / "extra.toml"
        extra_path.write_text("config\n")

        registry = {
            "services": [
                {
                    "id": "n8n",
                    "state_bucket": "selected_services",
                    "extra_templates": [{"src": "ignored", "dst": "docker/n8n/extra.toml"}],
                    "postgres": {"role": "n8n", "db": "n8n_db", "password_key": "N8N_DB_PASS"},
                }
            ]
        }
        state = State({"data_root": str(data_root)})

        with patch("rakkib.steps.services._load_registry", return_value=registry):
            services_step.remove_single_service(state, "n8n")

        mock_down.assert_called_once()
        assert not service_dir.exists()
        assert not (route_path / "n8n.caddy").exists()
        assert not data_dir.exists()
        assert not extra_path.exists()
        sql = mock_run.call_args.kwargs["input"]
        assert "DROP DATABASE IF EXISTS n8n_db;" in sql
        assert "DROP ROLE IF EXISTS n8n;" in sql

    @patch("rakkib.steps.services._run_named_hooks")
    def test_host_service_runs_remove_hooks(self, mock_hooks, tmp_path):
        data_root = tmp_path / "srv"
        registry = {
            "services": [
                {
                    "id": "openclaw",
                    "state_bucket": "selected_services",
                    "host_service": True,
                    "hooks": {"remove": ["openclaw_gateway_uninstall"]},
                }
            ]
        }
        state = State({"data_root": str(data_root)})

        with patch("rakkib.steps.services._load_registry", return_value=registry):
            services_step.remove_single_service(state, "openclaw")

        mock_hooks.assert_called_once()
        assert mock_hooks.call_args.args[0] == ["openclaw_gateway_uninstall"]


class TestVerify:
    @patch("rakkib.steps.services.subprocess.run")
    def test_host_service_uses_monitoring_path(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=0)
        state = State({
            "foundation_services": [],
            "selected_services": ["openclaw"],
        })

        result = services_step.verify(state)

        assert result.ok is True
        assert mock_run.call_args.args[0][2] == "http://127.0.0.1:18789/healthz"


class TestRestartService:
    @patch("rakkib.steps.services._run_named_hooks")
    def test_host_service_uses_restart_hooks(self, mock_hooks):
        registry = {
            "services": [
                {
                    "id": "openclaw",
                    "state_bucket": "selected_services",
                    "host_service": True,
                    "hooks": {"restart": ["openclaw_gateway_restart"]},
                }
            ]
        }
        state = State({"data_root": "/srv"})

        with patch("rakkib.steps.services._load_registry", return_value=registry):
            services_step.restart_service(state, "openclaw")

        mock_hooks.assert_called_once()
        assert mock_hooks.call_args.args[0] == ["openclaw_gateway_restart"]

    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.container_running")
    @patch("rakkib.steps.services.container_publishes_port")
    def test_all_running_passes(
        self,
        mock_port: MagicMock,
        mock_running: MagicMock,
        mock_repo: MagicMock,
        fake_repo: Path,
    ):
        mock_repo.return_value = fake_repo
        mock_running.return_value = True
        mock_port.return_value = True
        state = State({
            "foundation_services": ["nocodb"],
            "selected_services": [],
        })
        result = services_step.verify(state)
        assert result.ok is True

    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.container_running")
    def test_missing_container_fails(
        self,
        mock_running: MagicMock,
        mock_repo: MagicMock,
        fake_repo: Path,
    ):
        mock_repo.return_value = fake_repo
        mock_running.return_value = False
        state = State({
            "foundation_services": ["nocodb"],
            "selected_services": [],
        })
        result = services_step.verify(state)
        assert result.ok is False
        assert "nocodb" in result.message

    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.container_running")
    @patch("rakkib.steps.services.container_publishes_port")
    def test_port_not_published_fails_for_host_port_service(
        self,
        mock_port: MagicMock,
        mock_running: MagicMock,
        mock_repo: MagicMock,
    ):
        """A service with host_port=True must publish its port to pass verify."""
        mock_repo.return_value = Path(__file__).resolve().parent.parent / "src" / "rakkib" / "data"
        mock_running.return_value = True
        mock_port.return_value = False
        # transfer has host_port=True; if port is not published, verify must fail
        state = State({
            "foundation_services": [],
            "selected_services": ["transfer"],
        })
        result = services_step.verify(state)
        assert result.ok is False
        assert "does not publish port" in result.message

    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.container_running")
    @patch("rakkib.steps.services.container_publishes_port")
    def test_network_only_service_passes_without_host_port(
        self,
        mock_port: MagicMock,
        mock_running: MagicMock,
        mock_repo: MagicMock,
    ):
        """A service with host_port=False should pass verify even if port is not published."""
        mock_repo.return_value = Path(__file__).resolve().parent.parent / "src" / "rakkib" / "data"
        mock_running.return_value = True
        mock_port.return_value = False
        # dockge has host_port=False; verify should succeed without port check
        state = State({
            "foundation_services": ["dockge"],
            "selected_services": [],
        })
        result = services_step.verify(state)
        assert result.ok is True
        # container_publishes_port should NOT be called for host_port=False services
        mock_port.assert_not_called()
