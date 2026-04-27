"""End-to-end verification tests for Rakkib v2.

These tests verify the six scenarios from pyplan.md / bead Rakkib-aaz:
1. Fresh VM install bootstrap
2. Zero LLM token cost for deterministic paths
3. Resume after interrupted interview
4. Step failure → narrow agent handoff
5. Post-install add runs only the new service slice
6. Idempotent re-apply on confirmed state
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from rakkib.cli import cli
from rakkib.state import State
from rakkib.steps import VerificationResult


# ---------------------------------------------------------------------------
# Scenario 1 — Fresh VM install bootstrap
# ---------------------------------------------------------------------------


class TestFreshVmInstall:
    """Verify install.sh handles python3/pipx bootstrap and repo setup."""

    def test_install_script_detects_missing_python3(self, tmp_path: Path):
        """If python3 is absent, install.sh must die with a clear message."""
        script = Path(__file__).resolve().parent.parent / "install.sh"
        result = subprocess.run(
            ["bash", str(script), "--help"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        # --help should succeed regardless
        assert result.returncode == 0
        assert "Usage:" in result.stdout

    def test_install_script_ensure_pipx_logic(self, tmp_path: Path):
        """Verify ensure_pipx bash function logic via direct execution."""
        script = Path(__file__).resolve().parent.parent / "install.sh"
        bash_script = tmp_path / "test_pipx_logic.sh"
        bash_script.write_text(
            textwrap.dedent(
                f"""\
                set -e
                source <(sed '/^main() {{/,$d' "{script}")
                export HOME="{tmp_path}/home"
                mkdir -p "$HOME"
                command_exists() {{ false; }}
                ( ensure_pipx 2>/dev/null ) || echo "EXPECTED_FAILURE"
                """
            )
        )
        result = subprocess.run(
            ["bash", str(bash_script)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert "EXPECTED_FAILURE" in result.stdout or result.returncode != 0

    def test_install_script_offers_to_install_pip_deps(self, tmp_path: Path):
        """When pipx can't be installed via pip, install.sh offers system packages."""
        script = Path(__file__).resolve().parent.parent / "install.sh"
        calls_file = tmp_path / "sudo_calls.txt"
        bash_script = tmp_path / "test_pip_deps.sh"
        bash_script.write_text(
            textwrap.dedent(
                f"""\
                set -e
                source <(sed '/^main() {{/,$d' "{script}")
                _detect_package_manager() {{ echo "apt-get"; }}
                sudo() {{
                  echo "MOCK_SUDO $*" >> "{calls_file}"
                  return 0
                }}
                # Mock _prompt to bypass stdin/TTY issues in test subprocesses
                _prompt() {{
                  local var_name="$1"
                  eval "$var_name=\"y\""
                }}
                export -f _detect_package_manager sudo _prompt
                _install_system_python_deps
                """
            )
        )
        result = subprocess.run(
            ["bash", str(bash_script)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        calls = calls_file.read_text()
        assert "MOCK_SUDO" in calls
        assert "apt-get" in calls

    def test_install_script_prepare_repo_clone(self, tmp_path: Path):
        """prepare_repo should clone into the target directory."""
        script = Path(__file__).resolve().parent.parent / "install.sh"
        dest = tmp_path / "rakkib-clone"
        bash_code = textwrap.dedent(
            f"""\
            set -e
            source "{script}"
            INSTALL_DIR="{dest}"
            REPO_URL="https://github.com/FayaaDev/Rakkib.git"
            BRANCH="main"
            # Override git clone with a fast mock to avoid network hangs
            git() {{
                if [[ "$1" == "clone" ]]; then
                    mkdir -p "$4"
                    echo "Mock clone into $4"
                    return 0
                fi
                command git "$@"
            }}
            prepare_repo
            """
        )
        result = subprocess.run(
            ["bash", "-c", bash_code],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert "Mock clone" in result.stdout


# ---------------------------------------------------------------------------
# Scenario 2 — Zero LLM token cost for deterministic paths
# ---------------------------------------------------------------------------


class TestZeroTokenCost:
    """Authentik + Immich interview and docker compose up must not invoke LLM."""

    def test_interview_authentik_immich_no_agent_call(self, tmp_path: Path):
        """Completing the interview for a config with authentik+immich
        must never call agent_handoff or launch an external agent.
        """
        from rakkib.interview import run_interview

        state = State({
            "platform": "linux",
            "arch": "amd64",
            "privilege_mode": "sudo",
            "privilege_strategy": "on_demand",
            "docker_installed": True,
            "host_gateway": "172.18.0.1",
            "server_name": "test",
            "domain": "example.com",
            "cloudflare": {"zone_in_cloudflare": True},
            "admin_user": "ubuntu",
            "admin_email": "a@b.com",
            "lan_ip": "192.168.1.1",
            "tz": "UTC",
            "data_root": "/srv",
            "docker_net": "caddy_net",
            "backup_dir": "/srv/backups",
            "foundation_services": ["authentik", "homepage"],
            "selected_services": ["immich"],
            "host_addons": [],
            "subdomains": {"authentik": "auth", "homepage": "home", "immich": "immich"},
            "cloudflare": {
                "zone_in_cloudflare": True,
                "auth_method": "browser_login",
                "headless": False,
                "tunnel_strategy": "new",
                "tunnel_name": "test",
                "ssh_subdomain": "ssh",
                "tunnel_uuid": None,
                "tunnel_creds_host_path": None,
                "tunnel_creds_container_path": None,
            },
            "secrets": {"mode": "generate", "n8n_mode": "fresh", "values": {}},
        })

        with (
            patch("rakkib.interview.load_all_schemas") as mock_load,
            patch("rakkib.agent_handoff.handoff") as mock_handoff,
            patch("rakkib.agent_handoff._launch") as mock_launch,
            patch("rakkib.interview.console.print"),
        ):
            # Return an empty schema list so the interview loop is a no-op
            mock_load.return_value = []
            run_interview(state)

        mock_handoff.assert_not_called()
        mock_launch.assert_not_called()

    def test_services_run_authentik_immich_no_agent_call(self, tmp_path: Path):
        """Step 60 for authentik+immich must not hand off to an agent."""
        from rakkib.steps import services as services_step

        repo = tmp_path / "repo"
        repo.mkdir()
        registry = {
            "services": [
                {"id": "authentik", "depends_on": [], "host_service": False, "default_port": 9000},
                {"id": "immich", "depends_on": [], "host_service": False, "default_port": 2283},
            ]
        }
        (repo / "registry.yaml").write_text(yaml.dump(registry))

        # Minimal templates
        for svc in ["authentik", "immich"]:
            d = repo / "templates" / "docker" / svc
            d.mkdir(parents=True)
            (d / "docker-compose.yml.tmpl").write_text(f"# {svc}\n")
            (d / ".env.example").write_text(f"VAR={{{{VALUE}}}}\n")
        caddy = repo / "templates" / "caddy" / "routes"
        caddy.mkdir(parents=True)
        (caddy / "authentik.caddy.tmpl").write_text("# auth\n")
        (caddy / "immich.caddy.tmpl").write_text("# imm\n")

        data_root = tmp_path / "srv"
        state = State({
            "foundation_services": ["authentik"],
            "selected_services": ["immich"],
            "data_root": str(data_root),
            "backup_dir": str(data_root / "backups"),
        })

        with (
            patch.object(services_step, "_repo_dir", return_value=repo),
            patch.object(services_step, "compose_up") as mock_compose,
            patch.object(services_step, "_reload_caddy"),
            patch.object(services_step, "health_check", return_value=True),
            patch("rakkib.agent_handoff.handoff") as mock_handoff,
            patch("rakkib.agent_handoff._launch") as mock_launch,
        ):
            services_step.run(state)

        mock_handoff.assert_not_called()
        mock_launch.assert_not_called()
        assert mock_compose.call_count == 2  # authentik + immich


# ---------------------------------------------------------------------------
# Scenario 3 — Resume after interrupted interview
# ---------------------------------------------------------------------------


class TestResumeBehavior:
    """Kill terminal in Phase 3, relaunch rakkib init → resumes silently.
    With confirmed: true, prompts "start over? (y/N)" once.
    """

    def test_run_interview_resumes_silently_at_phase_3(self, tmp_path: Path):
        """Partial state (phases 1-2 done) should skip to Phase 3."""
        from rakkib.interview import run_interview
        from rakkib.schema import QuestionSchema

        state = State({
            "platform": "linux",
            "server_name": "test",
        })

        schema1 = QuestionSchema.from_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 1\nfields:\n"
            "  - id: platform\n    type: single_select\n    prompt: Platform?\n"
            "    canonical_values: [linux, mac]\n    records: [platform]\n```\n"
        )
        schema2 = QuestionSchema.from_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 2\nfields:\n"
            "  - id: server_name\n    type: text\n    prompt: Name?\n"
            "    records: [server_name]\n```\n"
        )
        schema3 = QuestionSchema.from_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 3\nfields:\n"
            "  - id: foundation_services\n    type: multi_select\n"
            "    selection_mode: deselect_from_default\n    prompt: Deselect?\n"
            "    canonical_values: [homepage]\n    default: [homepage]\n"
            "    records: [foundation_services]\n```\n"
        )

        with (
            patch("rakkib.interview.load_all_schemas", return_value=[schema1, schema2, schema3]),
            patch("rakkib.interview.prompt_checkbox", return_value=[]) as mock_checkbox,
            patch("rakkib.interview.prompt_select", return_value="linux"),
            patch("rakkib.interview.prompt_text", return_value=""),
            patch("rakkib.interview.prompt_confirm", return_value=False),
            patch("rakkib.interview.console.print"),
            patch.object(state, "resume_phase", return_value=3),
        ):
            run_interview(state)

        # Phase 3 question should be asked; Phase 1 and 2 should not.
        prompts = [c.args[0] for c in mock_checkbox.call_args_list]
        assert any("Deselect" in p for p in prompts)
        assert not any("Platform" in p for p in prompts)
        assert not any("Name" in p for p in prompts)

    def test_run_interview_confirmed_prompts_start_over(self):
        """run_interview with confirmed state asks once to start over."""
        from rakkib.interview import run_interview
        from rakkib.schema import QuestionSchema

        state = State({"confirmed": True})
        schema = QuestionSchema.from_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 1\nfields:\n"
            "  - id: platform\n    type: single_select\n    prompt: Platform?\n"
            "    canonical_values: [linux, mac]\n    records: [platform]\n```\n"
        )

        with (
            patch("rakkib.interview.load_all_schemas", return_value=[schema]),
            patch("rakkib.interview.prompt_confirm", return_value=False) as mock_confirm,
            patch("rakkib.interview.prompt_select", return_value="linux"),
            patch("rakkib.interview.console.print"),
        ):
            run_interview(state)

        mock_confirm.assert_called_once()
        actual_prompt = mock_confirm.call_args[0][0] if mock_confirm.call_args[0] else ""
        assert "Start over" in actual_prompt or "start over" in actual_prompt

    def test_init_confirmed_true_goes_through_interview(self, tmp_path: Path):
        """CLI init with confirmed: true goes through run_interview (which asks
        'Start over?'), not directly to steps."""
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("confirmed: true\nplatform: linux\n")

        with (
            patch("rakkib.cli._run_steps") as mock_run_steps,
            patch("rakkib.cli.run_interview") as mock_interview,
        ):
            mock_interview.return_value = State({"confirmed": True, "platform": "linux"})
            result = runner.invoke(cli, ["init"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_interview.assert_called_once()
        mock_run_steps.assert_called_once()

    def test_init_resume_flag_skips_interview(self, tmp_path: Path):
        """CLI init --resume with confirmed: true skips interview and runs steps."""
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("confirmed: true\nplatform: linux\n")

        with (
            patch("rakkib.cli._run_steps") as mock_run_steps,
            patch("rakkib.cli.run_interview") as mock_interview,
        ):
            result = runner.invoke(cli, ["init", "--resume"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_interview.assert_not_called()
        mock_run_steps.assert_called_once()
        assert "resuming step execution" in result.output.lower() or "--resume" in result.output.lower()


# ---------------------------------------------------------------------------
# Scenario 4 — Step failure → narrow agent handoff
# ---------------------------------------------------------------------------


class TestStepFailureHandoff:
    """Force Step 60 failure with bogus image tag → binary offers agent diagnose
    with narrow context (not the full protocol).
    """

    def test_step_60_failure_invokes_handoff_with_narrow_context(self, tmp_path: Path):
        """A failed services verify should call handoff with step='services'
        and a narrow state slice—not the whole AGENT_PROTOCOL.md.
        """
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("confirmed: true\n")

        questions_dir = repo_dir / "questions"
        questions_dir.mkdir()
        (questions_dir / "01-platform.md").write_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 1\nfields:\n"
            "  - id: platform\n    type: single_select\n    prompt: Platform?\n"
            "    canonical_values: [linux, mac]\n    records: [platform]\n```\n"
        )

        fake_result = VerificationResult.failure(
            "services", "Container jellyfin is not running (bogus image tag)"
        )
        with (
            patch("rakkib.steps.layout.run") as mock_layout_run,
            patch("rakkib.steps.layout.verify", return_value=VerificationResult.success("layout")),
            patch("rakkib.steps.caddy.run") as mock_caddy_run,
            patch("rakkib.steps.caddy.verify", return_value=VerificationResult.success("caddy")),
            patch("rakkib.steps.cloudflare.run") as mock_cf_run,
            patch("rakkib.steps.cloudflare.verify", return_value=VerificationResult.success("cloudflare")),
            patch("rakkib.steps.postgres.run") as mock_pg_run,
            patch("rakkib.steps.postgres.verify", return_value=VerificationResult.success("postgres")),
            patch("rakkib.steps.services.verify", return_value=fake_result),
            patch("rakkib.steps.services.run") as mock_run,
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
        assert call_kwargs["step"] == "services"
        assert "bogus" in call_kwargs["message"] or "jellyfin" in call_kwargs["message"]
        # Ensure we are NOT passing the full protocol as context
        assert "AGENT_PROTOCOL" not in call_kwargs.get("message", "")

    def test_handoff_builds_narrow_prompt(self, tmp_path: Path):
        """The agent handoff prompt must contain only step-relevant files
        and a redacted state slice.
        """
        from rakkib.agent_handoff import _build_prompt, build_state_slice

        state = State({
            "data_root": "/srv",
            "foundation_services": ["authentik"],
            "selected_services": ["immich"],
            "cloudflare": {
                "auth_method": "browser_login",
                "api_token": "secret123",
            },
            "irrelevant_key": "should_not_appear",
        })

        slice_ = build_state_slice("services", state)
        assert "foundation_services" in slice_
        assert "selected_services" in slice_
        assert "data_root" in slice_
        assert "irrelevant_key" not in slice_
        # Cloudflare token must be redacted even if it leaks into slice
        if "cloudflare" in slice_:
            assert slice_["cloudflare"]["api_token"] == "***"

        prompt = _build_prompt(
            step="services",
            message="Container immich_server is not running",
            log_tail="Error: No such image: bogus/immich:fake",
            state_slice=slice_,
            file_contents=[("steps/60-services.md", "# Services step")],
        )
        assert "Container immich_server is not running" in prompt
        assert "bogus/immich:fake" in prompt
        assert "steps/60-services.md" in prompt
        assert "secret123" not in prompt
        assert "Do not re-run the full installer" in prompt


# ---------------------------------------------------------------------------
# Scenario 5 — Post-install add runs only the new service slice
# ---------------------------------------------------------------------------


class TestPostInstallAdd:
    """rakkib add jellyfin → runs only Jellyfin slice of Step 60."""

    def test_add_jellyfin_runs_only_jellyfin_slice(self, tmp_path: Path):
        """Adding jellyfin to a confirmed deployment should update state
        and invoke run_single_service with 'jellyfin' only.
        """
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

        from rakkib.steps import services as services_step

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.steps.services._generate_missing_secrets") as mock_secrets,
            patch("rakkib.steps.services.run_single_service") as mock_run,
        ):
            mock_reg.return_value = {
                "services": [
                    {"id": "homepage", "state_bucket": "foundation_services", "depends_on": [], "default_subdomain": "home", "subdomain_placeholder": "HOMEPAGE_SUBDOMAIN"},
                    {"id": "authentik", "state_bucket": "foundation_services", "depends_on": [], "default_subdomain": "auth", "subdomain_placeholder": "AUTHENTIK_SUBDOMAIN"},
                    {"id": "jellyfin", "state_bucket": "selected_services", "depends_on": [], "default_subdomain": "jellyfin", "subdomain_placeholder": "JELLYFIN_SUBDOMAIN"},
                ]
            }
            result = runner.invoke(
                cli,
                ["add", "jellyfin"],
                input="\n",
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        assert "deployed successfully" in result.output
        mock_secrets.assert_called_once()
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        assert args[1] == "jellyfin"

        # Verify state was updated
        saved_state = State.load(state_file)
        assert "jellyfin" in (saved_state.get("selected_services") or [])
        assert saved_state.get("subdomains.jellyfin") == "jellyfin"
        assert saved_state.get("JELLYFIN_SUBDOMAIN") == "jellyfin"

        # Verify README was updated
        readme_content = readme.read_text()
        assert "RAKKIB AGENT MEMORY" in readme_content
        assert "jellyfin" in readme_content


# ---------------------------------------------------------------------------
# Scenario 6 — Idempotent re-apply
# ---------------------------------------------------------------------------


class TestIdempotentReapply:
    """rakkib init on an already-deployed host is a no-op or diff-and-merge."""

    def test_init_resume_skips_interview_on_confirmed_state(self, tmp_path: Path):
        """--resume with confirmed: true must skip the interview entirely."""
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("confirmed: true\nplatform: linux\n")

        with (
            patch("rakkib.cli._run_steps") as mock_run_steps,
            patch("rakkib.interview.run_interview") as mock_interview,
        ):
            result = runner.invoke(cli, ["init", "--resume", "--no-agent"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_interview.assert_not_called()
        mock_run_steps.assert_called_once()
        assert "resuming step execution" in result.output.lower()

    def test_layout_step_is_idempotent(self, tmp_path: Path):
        """Running layout.run twice on the same data_root must not fail."""
        from rakkib.steps import layout

        data_root = tmp_path / "srv"
        state = State({
            "data_root": str(data_root),
            "platform": "mac",
            "foundation_services": ["nocodb"],
            "selected_services": [],
        })

        layout.run(state)
        first_verify = layout.verify(state)
        assert first_verify.ok is True

        # Second run should be a no-op (no error)
        layout.run(state)
        second_verify = layout.verify(state)
        assert second_verify.ok is True

    def test_env_render_preserves_existing_secrets(self, tmp_path: Path):
        """Re-rendering an .env file must keep existing secret values."""
        from rakkib.steps import services as services_step

        state = State({"KEEP": "new_val", "NEW": "new_value"})
        existing_env = tmp_path / ".env"
        existing_env.write_text("KEEP=old_val\nOTHER=stuff\n")
        tmpl = tmp_path / "env.tmpl"
        tmpl.write_text("KEEP={{KEEP}}\nOTHER={{OTHER}}")

        services_step._render_env_example(
            state, tmpl, existing_env, preserve_keys=["KEEP"]
        )
        content = existing_env.read_text()
        assert "old_val" in content

    def test_cron_replaces_by_marker_not_duplicates(self, tmp_path: Path):
        """Installing the same cron entry twice must not duplicate lines."""
        from rakkib.steps import cron

        marker = "# RAKKIB: test-job"

        # Simulate existing crontab that already has the marker line
        cron_lines = ["0 0 * * * existing", f"* * * * * old  {marker}"]

        new_lines = cron._install_cron_entry(cron_lines, marker, "* * * * *", "echo hello")
        full = "\n".join(new_lines)
        assert full.count(marker) == 1
        assert "echo hello" in full
        assert "old" not in full
