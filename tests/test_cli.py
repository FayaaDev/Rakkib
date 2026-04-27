"""Tests for rakkib.cli."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from rakkib.cli import cli


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
            mock_run.return_value = MagicMock()
            result = runner.invoke(
                cli,
                ["init"],
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        assert "Rakkib init" in result.output
        mock_run.assert_called_once()

    def test_init_agent_option_noop(self, tmp_path: Path):
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
            mock_run.return_value = MagicMock()
            result = runner.invoke(
                cli,
                ["init", "--agent", "claude"],
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        assert "not yet implemented" in result.output
        mock_run.assert_called_once()

    def test_init_no_agent_option_noop(self, tmp_path: Path):
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
            mock_run.return_value = MagicMock()
            result = runner.invoke(
                cli,
                ["init", "--no-agent"],
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        assert "not yet implemented" in result.output
        mock_run.assert_called_once()

    def test_init_print_prompt_noop(self, tmp_path: Path):
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
            mock_run.return_value = MagicMock()
            result = runner.invoke(
                cli,
                ["init", "--print-prompt"],
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        assert "not yet implemented" in result.output
        mock_run.assert_called_once()


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
