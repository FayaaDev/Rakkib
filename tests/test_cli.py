"""Tests for rakkib.cli."""

from __future__ import annotations

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
        assert "No shim found" in result.output
