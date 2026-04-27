"""Tests for rakkib.agent_handoff."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rakkib.agent_handoff import (
    AgentName,
    _build_prompt,
    _launch,
    build_state_slice,
    find_agent,
    handoff,
    log_paths_for_step,
    question_files_for_step,
    read_log_tail,
    redact_state,
)
from rakkib.state import State


# ---------------------------------------------------------------------------
# find_agent
# ---------------------------------------------------------------------------


class TestFindAgent:
    def test_finds_first_available(self):
        with patch("rakkib.agent_handoff.shutil.which") as mock_which:
            mock_which.side_effect = lambda name: name == "claude"
            assert find_agent() == "claude"

    def test_prefers_preferred(self):
        with patch("rakkib.agent_handoff.shutil.which") as mock_which:
            mock_which.side_effect = lambda name: name in ("opencode", "claude")
            assert find_agent("claude") == "claude"

    def test_returns_none_when_missing(self):
        with patch("rakkib.agent_handoff.shutil.which", return_value=None):
            assert find_agent() is None

    def test_none_and_auto_are_ignored(self):
        with patch("rakkib.agent_handoff.shutil.which") as mock_which:
            mock_which.side_effect = lambda name: name == "opencode"
            assert find_agent("none") == "opencode"
            assert find_agent("auto") == "opencode"


# ---------------------------------------------------------------------------
# read_log_tail
# ---------------------------------------------------------------------------


class TestReadLogTail:
    def test_reads_last_lines(self, tmp_path: Path):
        log = tmp_path / "test.log"
        log.write_text("line1\nline2\nline3\nline4\nline5\n")
        assert read_log_tail(log, lines=3) == "line3\nline4\nline5\n"

    def test_returns_not_found(self, tmp_path: Path):
        missing = tmp_path / "missing.log"
        assert "not found" in read_log_tail(missing)

    def test_handles_empty_file(self, tmp_path: Path):
        log = tmp_path / "empty.log"
        log.write_text("")
        assert read_log_tail(log) == ""


# ---------------------------------------------------------------------------
# log_paths_for_step
# ---------------------------------------------------------------------------


class TestLogPathsForStep:
    def test_layout(self):
        state = State({"data_root": "/srv"})
        paths = log_paths_for_step("layout", state)
        assert paths == [Path("/srv/logs/layout.log")]

    def test_services_collects_per_service_logs(self):
        state = State({
            "data_root": "/srv",
            "foundation_services": ["authentik"],
            "selected_services": ["n8n"],
        })
        paths = log_paths_for_step("services", state)
        assert set(paths) == {
            Path("/srv/logs/step60-authentik.log"),
            Path("/srv/logs/step60-n8n.log"),
        }

    def test_verify_returns_empty(self):
        state = State({"data_root": "/srv"})
        assert log_paths_for_step("verify", state) == []


# ---------------------------------------------------------------------------
# redact_state
# ---------------------------------------------------------------------------


class TestRedactState:
    def test_redacts_secrets_subtree(self):
        data = {
            "secrets": {
                "mode": "generate",
                "values": {
                    "POSTGRES_PASSWORD": "hunter2",
                },
            },
            "platform": "linux",
        }
        result = redact_state(data)
        assert result["secrets"]["mode"] == "generate"
        assert result["secrets"]["values"] == "***REDACTED***"
        assert result["platform"] == "linux"

    def test_redacts_secret_keys(self):
        data = {
            "POSTGRES_PASSWORD": "hunter2",
            "AUTHENTIK_SECRET_KEY": "abc123",
            "domain": "example.com",
        }
        result = redact_state(data)
        assert result["POSTGRES_PASSWORD"] == "***"
        assert result["AUTHENTIK_SECRET_KEY"] == "***"
        assert result["domain"] == "example.com"

    def test_redacts_nested_dicts(self):
        data = {
            "cloudflare": {
                "tunnel_uuid": "abc",
                "api_token": "secret",
            },
        }
        result = redact_state(data)
        assert result["cloudflare"]["tunnel_uuid"] == "abc"
        assert result["cloudflare"]["api_token"] == "***"

    def test_leaves_lists_intact(self):
        data = {"selected_services": ["n8n", "immich"]}
        assert redact_state(data) == data


# ---------------------------------------------------------------------------
# build_state_slice
# ---------------------------------------------------------------------------


class TestBuildStateSlice:
    def test_extracts_relevant_keys(self):
        state = State({
            "data_root": "/srv",
            "platform": "linux",
            "admin_user": "alice",
            "irrelevant": "ignored",
        })
        slice_ = build_state_slice("layout", state)
        assert slice_["data_root"] == "/srv"
        assert slice_["platform"] == "linux"
        assert slice_["admin_user"] == "alice"
        assert "irrelevant" not in slice_

    def test_redacts_in_slice(self):
        state = State({
            "data_root": "/srv",
            "cloudflare": {
                "auth_method": "browser",
                "api_token": "secret123",
            },
        })
        slice_ = build_state_slice("cloudflare", state)
        assert slice_["cloudflare"]["api_token"] == "***"


# ---------------------------------------------------------------------------
# question_files_for_step
# ---------------------------------------------------------------------------


class TestQuestionFilesForStep:
    def test_reads_existing_files(self, tmp_path: Path):
        (tmp_path / "steps").mkdir()
        (tmp_path / "steps" / "10-layout.md").write_text("# Layout")
        files = question_files_for_step("layout", tmp_path)
        assert files == [("steps/10-layout.md", "# Layout")]

    def test_skips_missing_files(self, tmp_path: Path):
        files = question_files_for_step("layout", tmp_path)
        assert files == []

    def test_caddy_reads_multiple(self, tmp_path: Path):
        (tmp_path / "steps").mkdir()
        (tmp_path / "questions").mkdir()
        (tmp_path / "steps" / "30-caddy.md").write_text("# Caddy")
        (tmp_path / "questions" / "02-identity.md").write_text("# Identity")
        files = question_files_for_step("caddy", tmp_path)
        assert len(files) == 2


# ---------------------------------------------------------------------------
# _build_prompt
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    def test_includes_all_sections(self):
        prompt = _build_prompt(
            step="caddy",
            message="Container not running",
            log_tail="last line",
            state_slice={"docker_net": "caddy_net"},
            file_contents=[("steps/30-caddy.md", "# Caddy docs")],
        )
        assert "Rakkib step 'caddy' failed verification." in prompt
        assert "Container not running" in prompt
        assert "docker_net" in prompt
        assert "last line" in prompt
        assert "steps/30-caddy.md" in prompt
        assert "Do not re-run the full installer" in prompt

    def test_omits_files_when_empty(self):
        prompt = _build_prompt(
            step="layout",
            message="Missing dir",
            log_tail="",
            state_slice={},
            file_contents=[],
        )
        assert "Relevant documentation:" not in prompt
        assert "(no log output)" in prompt


# ---------------------------------------------------------------------------
# _launch
# ---------------------------------------------------------------------------


class TestLaunch:
    def test_opencode_invocation(self):
        with patch("rakkib.agent_handoff.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            _launch("opencode", "test prompt", repo_dir=Path("/repo"))
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0] == ["opencode", ".", "--prompt", "-"]
            assert kwargs["input"] == "test prompt"
            assert kwargs["cwd"] == "/repo"

    def test_claude_invocation(self):
        with patch("rakkib.agent_handoff.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            _launch("claude", "test prompt")
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0] == ["claude", "-p", "-"]

    def test_returns_exit_code(self):
        with patch("rakkib.agent_handoff.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=42)
            assert _launch("codex", "test prompt") == 42

    def test_raises_on_unknown_agent(self):
        with pytest.raises(ValueError, match="Unsupported agent"):
            _launch("unknown", "test prompt")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# handoff (integration-level)
# ---------------------------------------------------------------------------


class TestHandoff:
    def test_no_agent_skips(self, tmp_path: Path):
        state = State({"data_root": str(tmp_path)})
        with patch("rakkib.agent_handoff.console.print") as mock_print:
            result = handoff(
                step="layout",
                message="fail",
                log_path=None,
                state=state,
                repo_dir=tmp_path,
                no_agent=True,
            )
        assert result is False
        mock_print.assert_any_call("[dim]--no-agent set; skipping agent handoff.[/dim]")

    def test_print_prompt_returns_true(self, tmp_path: Path):
        state = State({"data_root": str(tmp_path)})
        with patch("rakkib.agent_handoff.console.print") as mock_print:
            result = handoff(
                step="layout",
                message="fail",
                log_path=None,
                state=state,
                repo_dir=tmp_path,
                print_prompt=True,
            )
        assert result is True
        assert any("Agent prompt:" in str(c) for c in mock_print.call_args_list)

    def test_no_available_agent_warns(self, tmp_path: Path):
        state = State({"data_root": str(tmp_path)})
        with (
            patch("rakkib.agent_handoff.find_agent", return_value=None),
            patch("rakkib.agent_handoff.console.print") as mock_print,
        ):
            result = handoff(
                step="layout",
                message="fail",
                log_path=None,
                state=state,
                repo_dir=tmp_path,
            )
        assert result is False
        assert any("No supported agent found" in str(c) for c in mock_print.call_args_list)

    def test_user_decline_skips(self, tmp_path: Path):
        state = State({"data_root": str(tmp_path)})
        with (
            patch("rakkib.agent_handoff.find_agent", return_value="opencode"),
            patch("rakkib.agent_handoff.Confirm.ask", return_value=False),
            patch("rakkib.agent_handoff.console.print") as mock_print,
        ):
            result = handoff(
                step="layout",
                message="fail",
                log_path=None,
                state=state,
                repo_dir=tmp_path,
            )
        assert result is False
        mock_print.assert_any_call("[dim]Agent handoff skipped.[/dim]")

    def test_launches_agent_on_confirm(self, tmp_path: Path):
        state = State({"data_root": str(tmp_path)})
        with (
            patch("rakkib.agent_handoff.find_agent", return_value="opencode"),
            patch("rakkib.agent_handoff.Confirm.ask", return_value=True),
            patch("rakkib.agent_handoff._launch", return_value=0) as mock_launch,
            patch("rakkib.agent_handoff.console.print") as mock_print,
        ):
            result = handoff(
                step="layout",
                message="fail",
                log_path=None,
                state=state,
                repo_dir=tmp_path,
            )
        assert result is True
        mock_launch.assert_called_once()
        assert any("Launching opencode" in str(c) for c in mock_print.call_args_list)

    def test_nonzero_exit_warns(self, tmp_path: Path):
        state = State({"data_root": str(tmp_path)})
        with (
            patch("rakkib.agent_handoff.find_agent", return_value="opencode"),
            patch("rakkib.agent_handoff.Confirm.ask", return_value=True),
            patch("rakkib.agent_handoff._launch", return_value=1),
            patch("rakkib.agent_handoff.console.print") as mock_print,
        ):
            result = handoff(
                step="layout",
                message="fail",
                log_path=None,
                state=state,
                repo_dir=tmp_path,
            )
        assert result is True
        assert any("exited with code 1" in str(c) for c in mock_print.call_args_list)
