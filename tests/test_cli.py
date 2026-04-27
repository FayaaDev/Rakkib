"""Tests for rakkib.cli."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from rakkib.cli import cli
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
            "foundation_services:\n  - nocodb\n  - authentik\n"
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


class TestAdd:
    def _make_registry(self, extra_services=None):
        services = [
            {"id": "postgres", "state_bucket": "always", "depends_on": [], "default_subdomain": None, "subdomain_placeholder": None},
            {"id": "homepage", "state_bucket": "foundation_services", "depends_on": [], "default_subdomain": "home", "subdomain_placeholder": "HOMEPAGE_SUBDOMAIN"},
            {"id": "authentik", "state_bucket": "foundation_services", "depends_on": ["postgres"], "default_subdomain": "auth", "subdomain_placeholder": "AUTHENTIK_SUBDOMAIN"},
            {"id": "nocodb", "state_bucket": "foundation_services", "depends_on": ["postgres"], "default_subdomain": "nocodb", "subdomain_placeholder": "NOCODB_SUBDOMAIN"},
            {"id": "n8n", "state_bucket": "selected_services", "depends_on": ["postgres"], "default_subdomain": "n8n", "subdomain_placeholder": "N8N_SUBDOMAIN"},
            {"id": "hermes", "state_bucket": "selected_services", "depends_on": ["authentik"], "default_subdomain": "hermes", "subdomain_placeholder": "HERMES_SUBDOMAIN"},
        ]
        if extra_services:
            services.extend(extra_services)
        return {"services": services}

    def test_add_invalid_service(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("confirmed: true\n")

        with patch("rakkib.steps.services._load_registry") as mock_reg:
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add", "invalid"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 1
        assert "not found in registry" in result.output

    def test_add_always_service(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("confirmed: true\n")

        with patch("rakkib.steps.services._load_registry") as mock_reg:
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add", "postgres"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "always deployed" in result.output

    def test_add_already_deployed(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("foundation_services:\n  - nocodb\n")

        with patch("rakkib.steps.services._load_registry") as mock_reg:
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add", "nocodb"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "already deployed" in result.output

    def test_add_missing_dependencies(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("foundation_services:\n  - homepage\n")

        with patch("rakkib.steps.services._load_registry") as mock_reg:
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add", "hermes"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 1
        assert "Missing dependencies" in result.output
        assert "authentik" in result.output

    def test_add_invalid_subdomain(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("foundation_services:\n  - homepage\n  - authentik\nselected_services: []\n")

        with patch("rakkib.steps.services._load_registry") as mock_reg:
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(
                cli,
                ["add", "n8n"],
                input="bad_subdomain!\n",
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 1
        assert "Subdomain must match" in result.output

    def test_add_success(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n  - authentik\n"
            "selected_services: []\n"
            "data_root: /srv\n"
            "domain: example.com\n"
        )
        readme = repo_dir / "README.md"
        readme.write_text("# Rakkib\n")

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.steps.services._generate_missing_secrets") as mock_secrets,
            patch("rakkib.steps.services.run_single_service") as mock_run,
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(
                cli,
                ["add", "n8n"],
                input="\n",
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        assert "deployed successfully" in result.output
        mock_secrets.assert_called_once()
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        assert args[1] == "n8n"

        # Verify state was updated
        saved_state = State.load(state_file)
        assert "n8n" in (saved_state.get("selected_services") or [])
        assert saved_state.get("subdomains.n8n") == "n8n"
        assert saved_state.get("N8N_SUBDOMAIN") == "n8n"

        # Verify README was updated
        readme_content = readme.read_text()
        assert "RAKKIB AGENT MEMORY" in readme_content
        assert "Foundation" in readme_content
        assert "Optional" in readme_content

    def test_add_custom_subdomain(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n  - authentik\n"
            "selected_services: []\n"
            "data_root: /srv\n"
            "domain: example.com\n"
        )
        readme = repo_dir / "README.md"
        readme.write_text("# Rakkib\n")

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.steps.services._generate_missing_secrets") as mock_secrets,
            patch("rakkib.steps.services.run_single_service") as mock_run,
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(
                cli,
                ["add", "n8n"],
                input="automation\n",
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        saved_state = State.load(state_file)
        assert saved_state.get("subdomains.n8n") == "automation"
        assert saved_state.get("N8N_SUBDOMAIN") == "automation"

    def test_add_updates_existing_readme_block(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n"
            "selected_services: []\n"
            "data_root: /srv\n"
            "domain: example.com\n"
        )
        readme = repo_dir / "README.md"
        readme.write_text(
            "# Rakkib\n\n"
            "<!-- BEGIN RAKKIB AGENT MEMORY -->\n"
            "## Deployed Services\n\n"
            "- **Foundation**: homepage\n"
            "- **Optional**: None\n"
            "- **Data Root**: /srv\n"
            "- **Domain**: example.com\n\n"
            "<!-- END RAKKIB AGENT MEMORY -->\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.steps.services._generate_missing_secrets") as mock_secrets,
            patch("rakkib.steps.services.run_single_service") as mock_run,
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(
                cli,
                ["add", "authentik"],
                input="\n",
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        content = readme.read_text()
        assert content.count("BEGIN RAKKIB AGENT MEMORY") == 1
        assert "homepage, authentik" in content


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
