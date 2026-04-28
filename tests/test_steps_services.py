"""Tests for rakkib.steps.services."""

from __future__ import annotations

import json
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
            {"id": "authentik", "depends_on": ["postgres"], "host_service": False, "default_port": 9000},
            {"id": "homepage", "depends_on": [], "host_service": False, "default_port": 3000},
            {"id": "openclaw", "depends_on": [], "host_service": True, "default_port": 18789},
        ]
    }
    (repo / "registry.yaml").write_text(yaml.dump(registry))

    # Templates
    for svc in ["postgres", "nocodb", "authentik", "homepage"]:
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
    for svc in ["nocodb", "authentik", "homepage"]:
        (caddy_dir / f"{svc}.caddy.tmpl").write_text(f"# {svc} route\n")

    return repo


class TestSelectedServiceDefs:
    def test_dependency_order(self, fake_repo: Path):
        state = State({
            "foundation_services": ["nocodb", "authentik"],
            "selected_services": ["homepage"],
        })
        registry = services_step._load_registry()
        defs = selected_service_defs(state, registry)
        ids = [d["id"] for d in defs]
        # homepage and authentik both have in-degree 0 (postgres not selected),
        # so they sort alphabetically: authentik, homepage, nocodb
        assert ids == ["authentik", "homepage", "nocodb"]

    def test_skips_unselected(self, fake_repo: Path):
        state = State({"foundation_services": ["nocodb"]})
        registry = services_step._load_registry()
        defs = selected_service_defs(state, registry)
        ids = [d["id"] for d in defs]
        assert "authentik" not in ids
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

    def test_generates_oidc_when_both_present(self):
        state = State({
            "foundation_services": ["nocodb", "authentik"],
        })
        services_step._generate_missing_secrets(state)
        assert state.get("NOCODB_OIDC_CLIENT_ID") is not None
        assert state.get("NOCODB_OIDC_CLIENT_SECRET") is not None

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
            "foundation_services": ["nocodb", "authentik"],
            "selected_services": ["n8n"],
            "secrets": {
                "n8n_mode": "fresh",
                "values": {
                    "AUTHENTIK_DB_PASS": "from-step4-authentik",
                    "NOCODB_DB_PASS": "from-step4-nocodb",
                    "N8N_DB_PASS": "from-step4-n8n",
                },
            },
        })
        services_step._generate_missing_secrets(state)
        assert state.get("AUTHENTIK_DB_PASS") == "from-step4-authentik"
        assert state.get("NOCODB_DB_PASS") == "from-step4-nocodb"
        assert state.get("N8N_DB_PASS") == "from-step4-n8n"

    def test_generates_when_secrets_values_empty(self):
        """When secrets.values has no entry, Step 5 should still generate."""
        state = State({
            "foundation_services": ["authentik"],
            "secrets": {"values": {}},
        })
        services_step._generate_missing_secrets(state)
        assert state.get("AUTHENTIK_DB_PASS") is not None
        assert len(state.get("AUTHENTIK_DB_PASS")) > 0


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
    def test_skips_host_service(
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
            "foundation_services": [],
            "selected_services": ["openclaw"],
            "data_root": str(data_root),
            "backup_dir": str(data_root / "backups"),
        })
        services_step.run(state)
        mock_compose.assert_not_called()

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
    def test_homepage_hook_writes_services_yaml(self, tmp_path):
        state = State(
            {
                "foundation_services": ["nocodb", "homepage"],
                "selected_services": ["dbhub"],
                "domain": "example.com",
                "subdomains": {"nocodb": "data", "dbhub": "sql"},
            }
        )
        registry = services_step._load_registry()
        service_hooks.homepage_services_yaml(state, {}, tmp_path, tmp_path, tmp_path / "hook.log", registry)
        content = (tmp_path / "data" / "homepage" / "config" / "services.yaml").read_text()
        assert "NocoDB" in content
        assert "https://data.example.com" in content
        assert "DBHub" in content

    def test_render_extra_templates(self, fake_repo, tmp_path):
        tmpl = fake_repo / "templates" / "docker" / "dbhub" / "dbhub.toml.tmpl"
        tmpl.parent.mkdir(parents=True, exist_ok=True)
        tmpl.write_text("# dbhub config")
        state = State({})
        svc = {
            "extra_templates": [
                {
                    "src": "templates/docker/dbhub/dbhub.toml.tmpl",
                    "dst": "docker/dbhub/dbhub.toml",
                }
            ]
        }
        services_step._render_extra_templates(state, svc, fake_repo, tmp_path)
        assert (tmp_path / "docker" / "dbhub" / "dbhub.toml").exists()

    @patch("rakkib.hooks.services.subprocess.run")
    @patch("rakkib.hooks.services.container_running", return_value=True)
    def test_sync_shared_artifacts_writes_kuma_monitors(self, _mock_running, mock_run, fake_repo, tmp_path):
        state = State(
            {
                "foundation_services": ["homepage", "uptime-kuma", "nocodb"],
                "selected_services": ["dbhub"],
                "domain": "example.com",
                "data_root": str(tmp_path),
                "subdomains": {
                    "homepage": "home",
                    "uptime-kuma": "status",
                    "nocodb": "data",
                    "dbhub": "sql",
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
        assert "dbhub" in service_ids
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
        svc = {"id": "authentik", "postgres": {"role": "authentik", "password_key": "AUTHENTIK_DB_PASS"}}

        with pytest.raises(RuntimeError, match="AUTHENTIK_DB_PASS"):
            service_hooks.service_postgres_login_preflight(state, svc, Path("."), Path("."), Path("hook.log"), {})

    @patch("rakkib.hooks.services.subprocess.run")
    def test_service_postgres_login_preflight_raises_on_failed_login(self, mock_run):
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="password authentication failed")
        state = State({"AUTHENTIK_DB_PASS": "bad-pass"})
        svc = {"id": "authentik", "postgres": {"role": "authentik", "password_key": "AUTHENTIK_DB_PASS"}}

        with pytest.raises(RuntimeError, match="service 'authentik'"):
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

        blueprint_dir = data_root / "data" / "authentik" / "blueprints" / "custom"
        blueprint_dir.mkdir(parents=True)
        (blueprint_dir / "n8n.yaml").write_text("blueprint\n")

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
        assert not (blueprint_dir / "n8n.yaml").exists()
        assert not extra_path.exists()
        sql = mock_run.call_args.kwargs["input"]
        assert "DROP DATABASE IF EXISTS n8n_db;" in sql
        assert "DROP ROLE IF EXISTS n8n;" in sql


class TestVerify:
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
        # dbhub has host_port=True; if port is not published, verify must fail
        state = State({
            "foundation_services": [],
            "selected_services": ["dbhub"],
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

    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.container_running")
    @patch("rakkib.steps.services.container_publishes_port")
    def test_authentik_container_name(self, mock_port, mock_running, mock_repo, fake_repo):
        mock_repo.return_value = fake_repo
        mock_running.return_value = True
        mock_port.return_value = True
        # Add authentik to fake registry
        registry = services_step._load_registry()
        state = State({
            "foundation_services": ["authentik"],
            "selected_services": [],
        })
        result = services_step.verify(state)
        assert result.ok is True
        mock_running.assert_any_call("authentik-server")
