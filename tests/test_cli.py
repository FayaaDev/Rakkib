"""Tests for rakkib.cli."""

from __future__ import annotations

import os
import shutil
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from rakkib.cli import _build_add_choices, _print_deployed_urls, cli
from rakkib.state import State


class TestInit:
    def test_init_runs_interview(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        questions_dir = repo_dir / "questions"
        questions_dir.mkdir()

        # Create minimal question files so load_all_schemas works
        (questions_dir / "01-platform.md").write_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 1\nfields:\n"
            "  - id: platform\n    type: single_select\n    prompt: Platform?\n"
            "    canonical_values: [linux, mac]\n    records: [platform]\n```\n"
        )

        with patch("rakkib.cli.run_interview") as mock_run:
            mock_run.return_value = State({"platform": "linux", "confirmed": False})
            result = runner.invoke(
                cli,
                ["init"],
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        assert "Rakkib init" in result.output
        mock_run.assert_called_once()

    def test_init_agent_option_accepted(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        questions_dir = repo_dir / "questions"
        questions_dir.mkdir()

        (questions_dir / "01-platform.md").write_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 1\nfields:\n"
            "  - id: platform\n    type: single_select\n    prompt: Platform?\n"
            "    canonical_values: [linux, mac]\n    records: [platform]\n```\n"
        )

        with patch("rakkib.cli.run_interview") as mock_run:
            mock_run.return_value = State({"platform": "linux", "confirmed": False})
            result = runner.invoke(
                cli,
                ["init", "--agent", "claude"],
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        assert "not yet implemented" not in result.output
        mock_run.assert_called_once()

    def test_init_no_agent_option_accepted(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        questions_dir = repo_dir / "questions"
        questions_dir.mkdir()

        (questions_dir / "01-platform.md").write_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 1\nfields:\n"
            "  - id: platform\n    type: single_select\n    prompt: Platform?\n"
            "    canonical_values: [linux, mac]\n    records: [platform]\n```\n"
        )

        with patch("rakkib.cli.run_interview") as mock_run:
            mock_run.return_value = State({"platform": "linux", "confirmed": False})
            result = runner.invoke(
                cli,
                ["init", "--no-agent"],
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        assert "not yet implemented" not in result.output
        mock_run.assert_called_once()

    def test_init_print_prompt_accepted(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        questions_dir = repo_dir / "questions"
        questions_dir.mkdir()

        (questions_dir / "01-platform.md").write_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 1\nfields:\n"
            "  - id: platform\n    type: single_select\n    prompt: Platform?\n"
            "    canonical_values: [linux, mac]\n    records: [platform]\n```\n"
        )

        with patch("rakkib.cli.run_interview") as mock_run:
            mock_run.return_value = State({"platform": "linux", "confirmed": False})
            result = runner.invoke(
                cli,
                ["init", "--print-prompt"],
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        assert "not yet implemented" not in result.output
        mock_run.assert_called_once()

    def test_init_confirmed_state_goes_through_interview(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        questions_dir = repo_dir / "questions"
        questions_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("confirmed: true\n")

        (questions_dir / "01-platform.md").write_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 1\nfields:\n"
            "  - id: platform\n    type: single_select\n    prompt: Platform?\n"
            "    canonical_values: [linux, mac]\n    records: [platform]\n```\n"
        )

        with (
            patch("rakkib.cli.run_interview") as mock_interview,
            patch("rakkib.cli._run_steps") as mock_steps,
        ):
            mock_interview.return_value = State({"platform": "linux", "confirmed": True})
            result = runner.invoke(
                cli,
                ["init"],
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        mock_interview.assert_called_once()
        mock_steps.assert_called_once()

    def test_init_resume_without_confirmed_state(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("platform: linux\n")

        result = runner.invoke(
            cli,
            ["init", "--resume"],
            obj={"repo_dir": repo_dir},
        )

        assert result.exit_code == 0
        assert "not confirmed" in result.output

    def test_init_step_failure_invokes_handoff(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        questions_dir = repo_dir / "questions"
        questions_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("confirmed: true\n")

        (questions_dir / "01-platform.md").write_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 1\nfields:\n"
            "  - id: platform\n    type: single_select\n    prompt: Platform?\n"
            "    canonical_values: [linux, mac]\n    records: [platform]\n```\n"
        )

        fake_result = MagicMock(ok=False, step="layout", message="bad", log_path=None)
        with (
            patch("rakkib.cli._check_docker", return_value=True),
            patch("rakkib.steps.layout.verify", return_value=fake_result),
            patch("rakkib.steps.layout.run") as mock_run,
            patch("rakkib.cli.handoff") as mock_handoff,
        ):
            result = runner.invoke(
                cli,
                ["init", "--resume", "--no-agent"],
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        mock_run.assert_called_once()
        mock_handoff.assert_called_once()
        call_kwargs = mock_handoff.call_args.kwargs
        assert call_kwargs["step"] == "layout"
        assert call_kwargs["message"] == "bad"
        assert call_kwargs["no_agent"] is True


class TestUninstall:
    def test_uninstall_removes_symlink(self, tmp_path: Path, monkeypatch):
        bin_dir = tmp_path / ".local" / "bin"
        bin_dir.mkdir(parents=True)
        shim = bin_dir / "rakkib"
        shim.symlink_to("/dev/null")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["uninstall"], input="y\n")
        assert result.exit_code == 0
        assert not shim.exists()

    def test_uninstall_no_shim(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["uninstall"], input="y\n")
        assert result.exit_code == 0
        assert "No rakkib CLI shim found" in result.output


class TestStatus:
    def test_status_unconfirmed_shows_message(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        result = runner.invoke(cli, ["status"], obj={"repo_dir": repo_dir})
        assert result.exit_code == 0
        assert "No confirmed deployment state found" in result.output

    def test_status_confirmed_shows_details(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "confirmed: true\n"
            "domain: example.com\n"
            "data_root: /srv\n"
            "platform: linux\n"
            "foundation_services:\n  - nocodb\n  - homepage\n"
            "selected_services:\n  - n8n\n"
            "host_addons:\n  - vergo_terminal\n"
            "subdomains:\n  nocodb: nocodb\n  n8n: n8n\n"
        )
        result = runner.invoke(cli, ["status"], obj={"repo_dir": repo_dir})
        assert result.exit_code == 0
        assert "example.com" in result.output
        assert "nocodb" in result.output
        assert "n8n" in result.output
        assert "vergo_terminal" in result.output


class TestDoctor:
    def test_doctor_json_output(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        with patch("rakkib.doctor.check_os") as mock_os, \
             patch("rakkib.doctor.check_arch") as mock_arch, \
             patch("rakkib.doctor.check_ram") as mock_ram, \
             patch("rakkib.doctor.check_disk") as mock_disk, \
             patch("rakkib.doctor.check_docker") as mock_docker, \
             patch("rakkib.doctor.check_compose") as mock_compose, \
             patch("rakkib.doctor.check_cloudflared_binary") as mock_cf, \
             patch("rakkib.doctor.check_public_ports") as mock_pp, \
             patch("rakkib.doctor.check_ssh_port") as mock_ssh, \
             patch("rakkib.doctor.check_domain_dns") as mock_dns, \
             patch("rakkib.doctor.check_cloudflare_readiness") as mock_cfr, \
             patch("rakkib.doctor.check_conflicts") as mock_conf:
            from rakkib.doctor import CheckResult
            mock_os.return_value = CheckResult("os", "ok", True, "Ubuntu detected")
            mock_arch.return_value = CheckResult("architecture", "ok", False, "amd64")
            mock_ram.return_value = CheckResult("ram", "ok", False, "8192 MB")
            mock_disk.return_value = CheckResult("disk", "ok", False, "50 GB")
            mock_docker.return_value = CheckResult("docker", "ok", True, "daemon reachable")
            mock_compose.return_value = CheckResult("compose", "ok", True, "v2")
            mock_cf.return_value = CheckResult("cloudflared_cli", "ok", False, "on PATH")
            mock_pp.return_value = CheckResult("public_ports", "ok", True, "80=free 443=free")
            mock_ssh.return_value = CheckResult("ssh_port", "ok", False, "listening")
            mock_dns.return_value = CheckResult("dns", "ok", False, "resolves")
            mock_cfr.return_value = [
                CheckResult("cloudflare_zone", "ok", False, "active"),
                CheckResult("cloudflare_auth", "ok", False, "browser_login"),
                CheckResult("cloudflare_creds", "ok", False, "present"),
            ]
            mock_conf.return_value = CheckResult("conflicts", "ok", False, "none")

            result = runner.invoke(cli, ["doctor", "--json"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["summary"]["ok"] > 0
        assert len(data["checks"]) > 0

    def test_doctor_exit_code_on_failure(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        with patch("rakkib.doctor.check_os") as mock_os, \
             patch("rakkib.doctor.check_arch") as mock_arch, \
             patch("rakkib.doctor.check_ram") as mock_ram, \
             patch("rakkib.doctor.check_disk") as mock_disk, \
             patch("rakkib.doctor.check_docker") as mock_docker, \
             patch("rakkib.doctor.check_compose") as mock_compose, \
             patch("rakkib.doctor.check_cloudflared_binary") as mock_cf, \
             patch("rakkib.doctor.check_public_ports") as mock_pp, \
             patch("rakkib.doctor.check_ssh_port") as mock_ssh, \
             patch("rakkib.doctor.check_domain_dns") as mock_dns, \
             patch("rakkib.doctor.check_cloudflare_readiness") as mock_cfr, \
             patch("rakkib.doctor.check_conflicts") as mock_conf:
            from rakkib.doctor import CheckResult
            mock_os.return_value = CheckResult("os", "fail", True, "unsupported")
            mock_arch.return_value = CheckResult("architecture", "ok", False, "amd64")
            mock_ram.return_value = CheckResult("ram", "ok", False, "8192 MB")
            mock_disk.return_value = CheckResult("disk", "ok", False, "50 GB")
            mock_docker.return_value = CheckResult("docker", "ok", True, "daemon reachable")
            mock_compose.return_value = CheckResult("compose", "ok", True, "v2")
            mock_cf.return_value = CheckResult("cloudflared_cli", "ok", False, "on PATH")
            mock_pp.return_value = CheckResult("public_ports", "ok", True, "80=free 443=free")
            mock_ssh.return_value = CheckResult("ssh_port", "ok", False, "listening")
            mock_dns.return_value = CheckResult("dns", "ok", False, "resolves")
            mock_cfr.return_value = [
                CheckResult("cloudflare_zone", "ok", False, "active"),
                CheckResult("cloudflare_auth", "ok", False, "browser_login"),
                CheckResult("cloudflare_creds", "ok", False, "present"),
            ]
            mock_conf.return_value = CheckResult("conflicts", "ok", False, "none")

            result = runner.invoke(cli, ["doctor"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 1
        assert "fail" in result.output
        assert "os" in result.output

    def test_doctor_interactive_prompts_for_fix(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        with patch("rakkib.doctor.check_os") as mock_os, \
             patch("rakkib.doctor.check_arch") as mock_arch, \
             patch("rakkib.doctor.check_ram") as mock_ram, \
             patch("rakkib.doctor.check_disk") as mock_disk, \
             patch("rakkib.doctor.check_docker") as mock_docker, \
             patch("rakkib.doctor.check_compose") as mock_compose, \
             patch("rakkib.doctor.check_cloudflared_binary") as mock_cf, \
             patch("rakkib.doctor.check_public_ports") as mock_pp, \
             patch("rakkib.doctor.check_ssh_port") as mock_ssh, \
             patch("rakkib.doctor.check_domain_dns") as mock_dns, \
             patch("rakkib.doctor.check_cloudflare_readiness") as mock_cfr, \
             patch("rakkib.doctor.check_conflicts") as mock_conf, \
             patch("rakkib.cli.attempt_fix_docker") as mock_fix:
            from rakkib.doctor import CheckResult
            mock_os.return_value = CheckResult("os", "ok", True, "Ubuntu")
            mock_arch.return_value = CheckResult("architecture", "ok", False, "amd64")
            mock_ram.return_value = CheckResult("ram", "ok", False, "8192 MB")
            mock_disk.return_value = CheckResult("disk", "ok", False, "50 GB")
            mock_docker.return_value = CheckResult("docker", "fail", True, "missing")
            mock_compose.return_value = CheckResult("compose", "fail", True, "missing")
            mock_cf.return_value = CheckResult("cloudflared_cli", "ok", False, "on PATH")
            mock_pp.return_value = CheckResult("public_ports", "ok", True, "80=free")
            mock_ssh.return_value = CheckResult("ssh_port", "ok", False, "listening")
            mock_dns.return_value = CheckResult("dns", "ok", False, "resolves")
            mock_cfr.return_value = [
                CheckResult("cloudflare_zone", "ok", False, "active"),
            ]
            mock_conf.return_value = CheckResult("conflicts", "ok", False, "none")
            mock_fix.return_value = "installed"

            result = runner.invoke(
                cli,
                ["doctor", "--interactive"],
                input="y\ny\n",
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 1
        mock_fix.assert_called_once()


class TestPull:
    def test_pull_only_prints_links_for_installed_services(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "confirmed: true\n"
            "domain: example.com\n"
            "foundation_services:\n  - homepage\n"
            "selected_services:\n  - n8n\n"
            "subdomains:\n"
            "  homepage: home\n"
            "  n8n: n8n\n"
            "  hermes: hermes\n"
        )

        def fake_run_steps(state: State, repo_dir: Path) -> bool:
            _print_deployed_urls(state)
            return True

        with (
            patch("rakkib.cli._ensure_prereqs", return_value=True),
            patch("rakkib.cli._run_steps", side_effect=fake_run_steps),
        ):
            result = runner.invoke(cli, ["pull"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "Deployed services:" in result.output
        assert "homepage" in result.output
        assert "https://home.example.com" in result.output
        assert "n8n" in result.output
        assert "https://n8n.example.com" in result.output
        assert "hermes" not in result.output
        assert "https://hermes.example.com" not in result.output


class TestAdd:
    def _make_registry(self, extra_services=None):
        services = [
            {
                "id": "postgres",
                "state_bucket": "always",
                "depends_on": [],
                "default_subdomain": None,
                "subdomain_placeholder": None,
                "notes": "Shared database backend.",
                "secrets": {"POSTGRES_PASSWORD": {"factory": "password"}},
            },
            {"id": "homepage", "state_bucket": "foundation_services", "depends_on": [], "default_subdomain": "home", "subdomain_placeholder": "HOMEPAGE_SUBDOMAIN", "notes": "Service dashboard."},
            {"id": "nocodb", "state_bucket": "foundation_services", "depends_on": ["postgres"], "default_subdomain": "nocodb", "subdomain_placeholder": "NOCODB_SUBDOMAIN", "notes": "No-code database UI.", "postgres": {"role": "nocodb", "db": "nocodb_db", "password_key": "NOCODB_DB_PASS"}},
            {"id": "n8n", "state_bucket": "selected_services", "depends_on": ["postgres"], "default_subdomain": "n8n", "subdomain_placeholder": "N8N_SUBDOMAIN", "notes": "Workflow automation.", "postgres": {"role": "n8n", "db": "n8n_db", "password_key": "N8N_DB_PASS"}, "homepage": {"category": "Automation"}},
            {"id": "hermes", "state_bucket": "selected_services", "depends_on": ["homepage"], "default_subdomain": "hermes", "subdomain_placeholder": "HERMES_SUBDOMAIN", "notes": "Internal assistant."},
            {"id": "openclaw", "state_bucket": "selected_services", "host_service": True, "depends_on": [], "default_subdomain": "claw", "subdomain_placeholder": "OPENCLAW_SUBDOMAIN", "notes": "AI assistant gateway.", "homepage": {"category": "AI"}},
        ]
        if extra_services:
            services.extend(extra_services)
        return {"services": services}

    def test_add_choices_group_selected_services_by_category(self):
        choices = _build_add_choices(
            State({"selected_services": ["n8n"]}), self._make_registry()
        )

        titles = [choice.title for choice in choices]
        assert "━━ Optional Services ━━" not in titles
        assert "━━ Automation ━━" in titles
        assert "━━ AI ━━" in titles
        assert "━━ Other ━━" in titles
        assert titles.index("━━ Automation ━━") < titles.index(
            "  n8n - Workflow automation"
        )

    def test_add_rejects_invalid_dependency_selection(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("confirmed: true\n")

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["hermes"]),
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 1
        assert "Invalid service selection" in result.output
        assert "hermes requires homepage" in result.output

    def test_add_no_changes_refreshes_selected_services(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n"
            "selected_services: []\n"
            "domain: example.com\n"
            "subdomains:\n"
            "  homepage: home\n"
            "HOMEPAGE_SUBDOMAIN: home\n"
        )
        call_order: list[str] = []

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["homepage"]),
            patch("rakkib.cli.prompt_confirm") as mock_confirm,
            patch("rakkib.steps.services._generate_missing_secrets") as mock_secrets,
            patch("rakkib.steps.postgres.run") as mock_postgres_run,
            patch("rakkib.steps.services.run") as mock_services_run,
        ):
            mock_reg.return_value = self._make_registry()
            mock_secrets.side_effect = lambda state: call_order.append("secrets")
            mock_postgres_run.side_effect = lambda state: call_order.append("postgres")
            mock_services_run.side_effect = lambda state: call_order.append("services")
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "No selection changes; refreshing selected services" in result.output
        assert "synced successfully" in result.output
        mock_confirm.assert_not_called()
        mock_secrets.assert_called_once()
        mock_postgres_run.assert_called_once()
        mock_services_run.assert_called_once()
        assert call_order == ["secrets", "postgres", "services"]

        saved_state = State.load(state_file)
        assert saved_state.get("foundation_services") == ["homepage"]
        assert saved_state.get("selected_services") == []
        assert saved_state.get("subdomains") == {"homepage": "home"}
        assert saved_state.get("HOMEPAGE_SUBDOMAIN") == "home"

    def test_add_preserves_always_service_secrets(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n"
            "selected_services: []\n"
            "POSTGRES_PASSWORD: keep-postgres\n"
            "secrets:\n"
            "  values:\n"
            "    POSTGRES_PASSWORD: keep-postgres\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["homepage"]),
            patch("rakkib.steps.services._generate_missing_secrets"),
            patch("rakkib.steps.postgres.run"),
            patch("rakkib.steps.services.run"),
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        saved_state = State.load(state_file)
        assert saved_state.get("POSTGRES_PASSWORD") == "keep-postgres"
        assert saved_state.get("secrets.values.POSTGRES_PASSWORD") == "keep-postgres"

    def test_add_backfills_host_gateway_for_host_services(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "platform: linux\n"
            "foundation_services: []\n"
            "selected_services: []\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["openclaw"]),
            patch("rakkib.cli.prompt_confirm", return_value=True),
            patch("rakkib.steps.services._generate_missing_secrets"),
            patch("rakkib.steps.postgres.run"),
            patch("rakkib.steps.services.run"),
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        saved_state = State.load(state_file)
        assert saved_state.get("selected_services") == ["openclaw"]
        assert saved_state.get("subdomains.openclaw") == "claw"
        assert saved_state.get("OPENCLAW_SUBDOMAIN") == "claw"
        assert saved_state.get("host_gateway") == "172.18.0.1"

    def test_add_service_argument_adds_service_without_checkbox(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "platform: linux\n"
            "foundation_services:\n  - homepage\n"
            "selected_services: []\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox") as mock_checkbox,
            patch("rakkib.cli.prompt_confirm", return_value=True),
            patch("rakkib.steps.services._generate_missing_secrets"),
            patch("rakkib.steps.postgres.run"),
            patch("rakkib.steps.services.run_single_service") as mock_run_single,
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add", "openclaw"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_checkbox.assert_not_called()
        mock_run_single.assert_called_once()
        assert mock_run_single.call_args.args[1] == "openclaw"
        saved_state = State.load(state_file)
        assert saved_state.get("foundation_services") == ["homepage"]
        assert saved_state.get("selected_services") == ["openclaw"]
        assert saved_state.get("host_gateway") == "172.18.0.1"

    def test_add_immich_argument_runs_single_service(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "platform: linux\n"
            "foundation_services:\n  - homepage\n"
            "selected_services:\n  - n8n\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox") as mock_checkbox,
            patch("rakkib.cli.prompt_confirm", return_value=True),
            patch("rakkib.steps.services._generate_missing_secrets"),
            patch("rakkib.steps.postgres.run") as mock_postgres,
            patch("rakkib.steps.services.run") as mock_run,
            patch("rakkib.steps.services.run_single_service") as mock_run_single,
        ):
            mock_reg.return_value = self._make_registry(
                extra_services=[
                    {
                        "id": "immich",
                        "state_bucket": "selected_services",
                        "depends_on": [],
                        "default_subdomain": "immich",
                        "subdomain_placeholder": "IMMICH_SUBDOMAIN",
                        "notes": "Photo library.",
                    }
                ]
            )
            result = runner.invoke(cli, ["add", "immich"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_checkbox.assert_not_called()
        mock_postgres.assert_called_once()
        mock_run.assert_not_called()
        mock_run_single.assert_called_once()
        assert mock_run_single.call_args.args[1] == "immich"
        saved_state = State.load(state_file)
        assert saved_state.get("selected_services") == ["n8n", "immich"]
        assert saved_state.get("subdomains.immich") == "immich"

    def test_add_service_argument_rejects_unknown_service(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".fss-state.yaml").write_text("confirmed: true\n")

        with patch("rakkib.steps.services._load_registry") as mock_reg:
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add", "missing"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 1
        assert "Unknown service 'missing'" in result.output

    def test_add_aborts_when_not_confirmed(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n  - nocodb\n"
            "selected_services:\n  - n8n\n"
            "subdomains:\n"
            "  homepage: home\n"
            "  n8n: n8n\n"
            "HOMEPAGE_SUBDOMAIN: home\n"
            "NOCODB_SUBDOMAIN: nocodb\n"
            "N8N_SUBDOMAIN: n8n\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["homepage", "nocodb"]),
            patch("rakkib.cli.prompt_confirm", return_value=False),
            patch("rakkib.steps.services.remove_single_service") as mock_remove,
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "Aborted" in result.output
        mock_remove.assert_not_called()

        saved_state = State.load(state_file)
        assert saved_state.get("selected_services") == ["n8n"]

    def test_add_syncs_selected_services(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n  - nocodb\n"
            "selected_services:\n  - n8n\n"
            "data_root: /srv\n"
            "domain: example.com\n"
            "subdomains:\n"
            "  homepage: home\n"
            "  n8n: n8n\n"
            "HOMEPAGE_SUBDOMAIN: home\n"
            "NOCODB_SUBDOMAIN: nocodb\n"
            "N8N_SUBDOMAIN: n8n\n"
        )
        call_order: list[str] = []

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["homepage", "nocodb"]),
            patch("rakkib.cli.prompt_confirm", return_value=True),
            patch("rakkib.steps.services.remove_single_service") as mock_remove,
            patch("rakkib.steps.services._generate_missing_secrets") as mock_secrets,
            patch("rakkib.steps.postgres.run") as mock_postgres_run,
            patch("rakkib.steps.services.run") as mock_services_run,
        ):
            mock_reg.return_value = self._make_registry()
            mock_secrets.side_effect = lambda state: call_order.append("secrets")
            mock_postgres_run.side_effect = lambda state: call_order.append("postgres")
            mock_services_run.side_effect = lambda state: call_order.append("services")
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "synced successfully" in result.output
        assert [call.args[1] for call in mock_remove.call_args_list] == ["n8n"]
        mock_secrets.assert_called_once()
        mock_postgres_run.assert_called_once()
        mock_services_run.assert_called_once()
        assert call_order == ["secrets", "postgres", "services"]

        saved_state = State.load(state_file)
        assert saved_state.get("foundation_services") == ["homepage", "nocodb"]
        assert saved_state.get("selected_services") == []
        assert saved_state.get("subdomains") == {"homepage": "home", "nocodb": "nocodb"}
        assert saved_state.get("HOMEPAGE_SUBDOMAIN") == "home"
        assert saved_state.get("NOCODB_SUBDOMAIN") == "nocodb"
        assert saved_state.get("N8N_SUBDOMAIN") is None

    def test_add_uses_spinner_when_applying_changes(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n"
            "selected_services: []\n"
            "domain: example.com\n"
            "subdomains:\n"
            "  homepage: home\n"
            "HOMEPAGE_SUBDOMAIN: home\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["homepage", "openclaw"]),
            patch("rakkib.cli.prompt_confirm", return_value=True),
            patch("rakkib.cli.progress_spinner", return_value=nullcontext()) as mock_spinner,
            patch("rakkib.steps.services._generate_missing_secrets"),
            patch("rakkib.steps.postgres.run"),
            patch("rakkib.steps.services.run_single_service"),
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_spinner.assert_called_once_with("Applying service changes...")
        saved_state = State.load(state_file)
        assert saved_state.get("selected_services") == ["openclaw"]


class TestUninstallPathBlock:
    def test_uninstall_removes_path_block(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create fake .bashrc with the marker block
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text(
            "some config\n"
            "# Added by Rakkib: user-local bin on PATH\n"
            'case ":$PATH:" in\n'
            '  *":$HOME/.local/bin:"*) ;;\n'
            '  *) export PATH="$HOME/.local/bin:$PATH" ;;\n'
            "esac\n"
            "more config\n"
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["uninstall"], input="y\n")
        assert result.exit_code == 0
        content = bashrc.read_text()
        assert "# Added by Rakkib" not in content
        assert "some config" in content
        assert "more config" in content

    def test_uninstall_no_path_block(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text("some config\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["uninstall"], input="y\n")
        assert result.exit_code == 0
        assert "No managed PATH block" in result.output


class TestAuth:
    def test_auth_root(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 0)
        runner = CliRunner()
        result = runner.invoke(cli, ["auth", "sudo"])
        assert result.exit_code == 0
        assert "Already running as root" in result.output

    def test_auth_sudo_ready(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 1000)
        monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/sudo" if cmd == "sudo" else None)

        runner = CliRunner()
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = runner.invoke(cli, ["auth", "sudo"])
        assert result.exit_code == 0
        assert "Sudo is ready" in result.output

    def test_auth_sudo_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 1000)
        monkeypatch.setattr(shutil, "which", lambda _cmd: None)
        runner = CliRunner()
        result = runner.invoke(cli, ["auth", "sudo"])
        assert result.exit_code == 1
        assert "sudo is required" in result.output

    def test_auth_help(self, tmp_path: Path):
        runner = CliRunner()
        result = runner.invoke(cli, ["auth", "--help"])
        assert result.exit_code == 0


class TestPrivileged:
    def test_privileged_check_root(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 0)
        runner = CliRunner()
        result = runner.invoke(cli, ["privileged", "check"])
        assert result.exit_code == 0
        assert "running as root" in result.output

    def test_privileged_check_non_root(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 1000)
        runner = CliRunner()
        result = runner.invoke(cli, ["privileged", "check"])
        assert result.exit_code == 1
        assert "root shell" in result.output

    def test_privileged_ensure_layout(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 0)
        data_root = tmp_path / "srv"
        state_file = tmp_path / ".fss-state.yaml"
        state_file.write_text("admin_user: testuser\n")

        runner = CliRunner()
        with patch("shutil.chown") as mock_chown:
            result = runner.invoke(
                cli,
                ["privileged", "ensure-layout", "--state", str(state_file), "--data-root", str(data_root)],
            )
        assert result.exit_code == 0
        assert data_root.exists()
        assert (data_root / "docker").exists()
        mock_chown.assert_called()

    def test_privileged_fix_repo_owner(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 0)
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = tmp_path / ".fss-state.yaml"
        state_file.write_text("admin_user: testuser\n")

        runner = CliRunner()
        with patch("shutil.chown") as mock_chown:
            result = runner.invoke(
                cli,
                ["privileged", "fix-repo-owner", "--state", str(state_file), "--repo-dir", str(repo_dir)],
            )
        assert result.exit_code == 0
        mock_chown.assert_called()


class TestCheckDocker:
    def test_docker_missing_aborts(self):
        with (
            patch("rakkib.cli.shutil.which", return_value=None),
            patch("rakkib.tui.prompt_confirm", return_value=False),
        ):
            from rakkib.cli import _check_docker
            assert _check_docker() is False

    def test_docker_available_passes(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Docker Compose version v2.24.0"
        with (
            patch("rakkib.cli.shutil.which", return_value="/usr/bin/docker"),
            patch("rakkib.cli.subprocess.run", return_value=mock_result),
        ):
            from rakkib.cli import _check_docker
            assert _check_docker() is True

    def test_compose_missing_decline_aborts(self):
        compose_missing = MagicMock()
        compose_missing.returncode = 1
        compose_missing.stdout = ""
        with (
            patch("rakkib.cli.shutil.which", return_value="/usr/bin/docker"),
            patch("rakkib.cli.subprocess.run", return_value=compose_missing),
            patch("rakkib.tui.prompt_confirm", return_value=False),
        ):
            from rakkib.cli import _check_docker
            assert _check_docker() is False

    def test_compose_missing_accept_installs(self):
        compose_missing = MagicMock()
        compose_missing.returncode = 1
        compose_missing.stdout = ""
        compose_ok = MagicMock()
        compose_ok.returncode = 0
        compose_ok.stdout = "Docker Compose version v2.35.1"
        with (
            patch("rakkib.cli.shutil.which", return_value="/usr/bin/docker"),
            patch("rakkib.cli.subprocess.run", side_effect=[compose_missing, compose_ok]),
            patch("rakkib.tui.prompt_confirm", return_value=True),
            patch("rakkib.doctor.attempt_fix_compose", return_value="docker compose plugin installed successfully."),
        ):
            from rakkib.cli import _check_docker
            assert _check_docker() is True
