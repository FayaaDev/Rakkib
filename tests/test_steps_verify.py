"""Tests for rakkib.steps.verify."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rakkib.state import State
from rakkib.steps import VerificationResult
from rakkib.steps import verify as verify_step


class TestCollectVerifications:
    def test_collects_all_results(self):
        state = State({})
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(verify=lambda s: VerificationResult.success("layout")),
                "rakkib.steps.caddy": MagicMock(verify=lambda s: VerificationResult.success("caddy")),
                "rakkib.steps.postgres": MagicMock(verify=lambda s: VerificationResult.success("postgres")),
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            results = verify_step._collect_verifications(state)
        assert len(results) == 5
        assert all(r.ok for r in results)

    def test_handles_import_error(self):
        state = State({})
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "rakkib.steps.postgres":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            results = verify_step._collect_verifications(state)

        postgres_results = [r for r in results if r.step == "postgres"]
        assert len(postgres_results) == 1
        assert postgres_results[0].ok is False
        assert "not found" in postgres_results[0].message

    def test_handles_failure(self):
        state = State({})
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(
                    verify=lambda s: VerificationResult.failure("layout", "boom")
                ),
                "rakkib.steps.caddy": MagicMock(verify=lambda s: VerificationResult.success("caddy")),
                "rakkib.steps.postgres": MagicMock(verify=lambda s: VerificationResult.success("postgres")),
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            results = verify_step._collect_verifications(state)
        assert any(not r.ok for r in results)
        failed = [r for r in results if not r.ok]
        assert failed[0].step == "layout"


class TestVerify:
    def test_success_when_all_pass(self):
        state = State({})
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(verify=lambda s: VerificationResult.success("layout")),
                "rakkib.steps.caddy": MagicMock(verify=lambda s: VerificationResult.success("caddy")),
                "rakkib.steps.postgres": MagicMock(verify=lambda s: VerificationResult.success("postgres")),
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            result = verify_step.verify(state)
        assert result.ok is True
        assert "All sub-verifications passed" in result.message

    def test_failure_aggregates(self):
        state = State({})
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(
                    verify=lambda s: VerificationResult.failure("layout", "bad")
                ),
                "rakkib.steps.caddy": MagicMock(
                    verify=lambda s: VerificationResult.failure("caddy", "worse")
                ),
                "rakkib.steps.postgres": MagicMock(verify=lambda s: VerificationResult.success("postgres")),
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            result = verify_step.verify(state)
        assert result.ok is False
        assert "layout: bad" in result.message
        assert "caddy: worse" in result.message
        assert result.state_slice is not None
        assert "layout" in result.state_slice["failed_steps"]
        assert "caddy" in result.state_slice["failed_steps"]


class TestRun:
    def test_prints_summary_on_failure(self, capsys):
        state = State({})
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(
                    verify=lambda s: VerificationResult.failure("layout", "bad")
                ),
                "rakkib.steps.caddy": MagicMock(verify=lambda s: VerificationResult.success("caddy")),
                "rakkib.steps.postgres": MagicMock(verify=lambda s: VerificationResult.success("postgres")),
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            verify_step.run(state)
        captured = capsys.readouterr()
        assert "VERIFICATION SUMMARY" in captured.out
        assert "HANDOFF PROMPT" in captured.out

    def test_prints_success_when_all_pass(self, capsys):
        state = State({})
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(verify=lambda s: VerificationResult.success("layout")),
                "rakkib.steps.caddy": MagicMock(verify=lambda s: VerificationResult.success("caddy")),
                "rakkib.steps.postgres": MagicMock(verify=lambda s: VerificationResult.success("postgres")),
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            verify_step.run(state)
        captured = capsys.readouterr()
        assert "All verification checks passed." in captured.out
