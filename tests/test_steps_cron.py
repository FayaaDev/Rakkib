"""Tests for rakkib.steps.cron."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rakkib.state import State
from rakkib.steps import VerificationResult
from rakkib.steps import cron as cron_step


class TestIsRoot:
    @patch("rakkib.steps.cron.os.geteuid", return_value=0)
    def test_returns_true_when_root(self, mock_geteuid):
        assert cron_step._is_root() is True

    @patch("rakkib.steps.cron.os.geteuid", return_value=1000)
    def test_returns_false_when_not_root(self, mock_geteuid):
        assert cron_step._is_root() is False


class TestWriteCrontab:
    @patch("rakkib.steps.cron.subprocess.run")
    def test_writes_lines(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=0)
        cron_step._write_crontab(["line1", "line2"])
        assert mock_run.call_count == 1
        assert "line1\nline2\n" in mock_run.call_args[1]["input"]

    @patch("rakkib.steps.cron.subprocess.run")
    def test_writes_for_user(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=0)
        cron_step._write_crontab(["line1"], user="admin")
        assert mock_run.call_args[0][0] == ["crontab", "-u", "admin", "-"]


class TestInstallCronEntry:
    def test_adds_new_entry(self):
        lines = ["# existing"]
        result = cron_step._install_cron_entry(lines, "# MARK", "0 * * * *", "/bin/script")
        assert any("# MARK" in line for line in result)
        assert "/bin/script" in result[-1]

    def test_replaces_existing_entry(self):
        lines = ["0 0 * * * /bin/old  # MARK"]
        result = cron_step._install_cron_entry(lines, "# MARK", "0 * * * *", "/bin/new")
        assert len([l for l in result if "# MARK" in l]) == 1
        assert "/bin/new" in result[-1]
        assert "/bin/old" not in result[-1]

    def test_does_not_duplicate(self):
        lines = ["0 0 * * * /bin/old  # MARK", "# other"]
        result = cron_step._install_cron_entry(lines, "# MARK", "0 * * * *", "/bin/new")
        assert len([l for l in result if "# MARK" in l]) == 1


class TestCrontabLines:
    @patch("rakkib.steps.cron.subprocess.run")
    def test_reads_lines(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=0, stdout="line1\nline2\n")
        lines = cron_step._crontab_lines()
        assert lines == ["line1", "line2"]

    @patch("rakkib.steps.cron.subprocess.run")
    def test_empty_when_no_crontab(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        lines = cron_step._crontab_lines()
        assert lines == []


class TestRun:
    @patch("rakkib.steps.cron._crontab_lines")
    @patch("rakkib.steps.cron._write_crontab")
    @patch("rakkib.steps.cron.render_file")
    @patch("rakkib.steps.cron.shutil.copy2")
    @patch("pathlib.Path.exists")
    def test_installs_openclaw_cron_when_selected(
        self,
        mock_exists: MagicMock,
        mock_copy: MagicMock,
        mock_render: MagicMock,
        mock_write: MagicMock,
        mock_read: MagicMock,
        tmp_path: Path,
    ):
        def _create_file(src, dst, state):
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            Path(dst).write_text("# rendered\n")

        mock_render.side_effect = _create_file
        mock_read.return_value = []
        mock_exists.return_value = True
        data_root = tmp_path / "srv"
        backup_dir = data_root / "backups"
        state = State({
            "data_root": str(data_root),
            "backup_dir": str(backup_dir),
            "platform": "linux",
            "admin_user": "admin",
            "selected_services": ["openclaw"],
        })
        cron_step.run(state)

        written_lines = mock_write.call_args[0][0]
        assert any("# RAKKIB: claw-healthcheck" in line for line in written_lines)
        assert any("# RAKKIB: claw-memory-alert" in line for line in written_lines)

    @patch("rakkib.steps.cron._is_root")
    @patch("rakkib.steps.cron._crontab_lines")
    @patch("rakkib.steps.cron._write_crontab")
    @patch("rakkib.steps.cron.render_file")
    @patch("rakkib.steps.cron.shutil.copy2")
    def test_run_as_root_uses_admin_user_crontab(
        self,
        mock_copy: MagicMock,
        mock_render: MagicMock,
        mock_write: MagicMock,
        mock_read: MagicMock,
        mock_is_root: MagicMock,
        tmp_path: Path,
    ):
        def _create_file(src, dst, state):
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            Path(dst).write_text("# rendered\n")

        mock_is_root.return_value = True
        mock_render.side_effect = _create_file
        mock_read.return_value = []
        data_root = tmp_path / "srv"
        backup_dir = data_root / "backups"
        state = State({
            "data_root": str(data_root),
            "backup_dir": str(backup_dir),
            "platform": "linux",
            "admin_user": "admin",
            "selected_services": [],
        })
        cron_step.run(state)
        mock_read.assert_called_once_with("admin")
        mock_write.assert_called_once()

    @patch("rakkib.steps.cron._crontab_lines")
    @patch("rakkib.steps.cron._write_crontab")
    @patch("rakkib.steps.cron.render_file")
    @patch("rakkib.steps.cron.shutil.copy2")
    def test_run_skips_openclaw_on_non_linux(
        self,
        mock_copy: MagicMock,
        mock_render: MagicMock,
        mock_write: MagicMock,
        mock_read: MagicMock,
        tmp_path: Path,
    ):
        def _create_file(src, dst, state):
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            Path(dst).write_text("# rendered\n")

        mock_render.side_effect = _create_file
        mock_read.return_value = []
        data_root = tmp_path / "srv"
        backup_dir = data_root / "backups"
        state = State({
            "data_root": str(data_root),
            "backup_dir": str(backup_dir),
            "platform": "mac",
            "admin_user": "admin",
            "selected_services": ["openclaw"],
        })
        cron_step.run(state)
        written_lines = mock_write.call_args[0][0]
        assert not any("claw-healthcheck" in line for line in written_lines)


class TestVerify:
    @patch("rakkib.steps.cron._crontab_lines")
    def test_passes_when_all_present(self, mock_read: MagicMock, tmp_path: Path):
        mock_read.return_value = [
            "30 2 * * * /srv/backups/backup-local.sh  # RAKKIB: backup-local",
            "*/5 * * * * bash /home/user/.local/bin/cloudflared-healthcheck.sh  # RAKKIB: cloudflared-healthcheck",
        ]
        data_root = tmp_path / "srv"
        backup_dir = data_root / "backups"
        backup_dir.mkdir(parents=True)
        (backup_dir / "backup-local.sh").write_text("#!/bin/bash\n")
        (backup_dir / "backup-local.sh").chmod(0o755)
        (backup_dir / "restore-local.sh").write_text("#!/bin/bash\n")
        (backup_dir / "restore-local.sh").chmod(0o755)
        (backup_dir / "healthchecks").mkdir()
        (backup_dir / "healthchecks" / "cloudflared-healthcheck.sh").write_text("#!/bin/bash\n")
        (backup_dir / "healthchecks" / "cloudflared-healthcheck.sh").chmod(0o755)

        state = State({
            "data_root": str(data_root),
            "backup_dir": str(backup_dir),
            "platform": "linux",
            "selected_services": [],
        })
        result = cron_step.verify(state)
        assert result.ok is True

    @patch("rakkib.steps.cron._crontab_lines")
    def test_fails_when_backup_script_not_executable(self, mock_read: MagicMock, tmp_path: Path):
        mock_read.return_value = ["30 2 * * * /srv/backups/backup-local.sh  # RAKKIB: backup-local"]
        data_root = tmp_path / "srv"
        backup_dir = data_root / "backups"
        backup_dir.mkdir(parents=True)
        (backup_dir / "backup-local.sh").write_text("#!/bin/bash\n")
        # NOT executable

        state = State({
            "data_root": str(data_root),
            "backup_dir": str(backup_dir),
            "platform": "linux",
            "selected_services": [],
        })
        result = cron_step.verify(state)
        assert result.ok is False
        assert "not executable" in result.message

    @patch("rakkib.steps.cron._crontab_lines")
    def test_fails_when_marker_missing(self, mock_read: MagicMock, tmp_path: Path):
        mock_read.return_value = []
        data_root = tmp_path / "srv"
        backup_dir = data_root / "backups"
        backup_dir.mkdir(parents=True)
        (backup_dir / "backup-local.sh").write_text("#!/bin/bash\n")
        (backup_dir / "backup-local.sh").chmod(0o755)
        (backup_dir / "restore-local.sh").write_text("#!/bin/bash\n")
        (backup_dir / "restore-local.sh").chmod(0o755)

        state = State({
            "data_root": str(data_root),
            "backup_dir": str(backup_dir),
            "platform": "linux",
            "selected_services": [],
        })
        result = cron_step.verify(state)
        assert result.ok is False
        assert "Missing cron entry" in result.message

    @patch("rakkib.steps.cron._crontab_lines")
    def test_fails_when_healthcheck_not_executable(self, mock_read: MagicMock, tmp_path: Path):
        mock_read.return_value = [
            "30 2 * * * /srv/backups/backup-local.sh  # RAKKIB: backup-local",
        ]
        data_root = tmp_path / "srv"
        backup_dir = data_root / "backups"
        backup_dir.mkdir(parents=True)
        (backup_dir / "backup-local.sh").write_text("#!/bin/bash\n")
        (backup_dir / "backup-local.sh").chmod(0o755)
        (backup_dir / "restore-local.sh").write_text("#!/bin/bash\n")
        (backup_dir / "restore-local.sh").chmod(0o755)
        (backup_dir / "healthchecks").mkdir()
        (backup_dir / "healthchecks" / "cloudflared-healthcheck.sh").write_text("#!/bin/bash\n")
        # NOT executable

        state = State({
            "data_root": str(data_root),
            "backup_dir": str(backup_dir),
            "platform": "linux",
            "selected_services": [],
        })
        result = cron_step.verify(state)
        assert result.ok is False
        assert "not executable" in result.message

    @patch("rakkib.steps.cron._crontab_lines")
    @patch("pathlib.Path.home", return_value=Path("/tmp/fake_home"))
    def test_fails_when_openclaw_markers_missing(self, mock_home: MagicMock, mock_read: MagicMock, tmp_path: Path):
        mock_read.return_value = [
            "30 2 * * * /srv/backups/backup-local.sh  # RAKKIB: backup-local",
        ]
        data_root = tmp_path / "srv"
        backup_dir = data_root / "backups"
        backup_dir.mkdir(parents=True)
        (backup_dir / "backup-local.sh").write_text("#!/bin/bash\n")
        (backup_dir / "backup-local.sh").chmod(0o755)
        (backup_dir / "restore-local.sh").write_text("#!/bin/bash\n")
        (backup_dir / "restore-local.sh").chmod(0o755)

        state = State({
            "data_root": str(data_root),
            "backup_dir": str(backup_dir),
            "platform": "linux",
            "selected_services": ["openclaw"],
        })
        result = cron_step.verify(state)
        assert result.ok is False
        assert "claw-healthcheck" in result.message
