"""Snapshot regression test for Phase 3b registry-driven rendering."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

from rakkib.state import State
from rakkib.steps import caddy, postgres, services


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
STATE_FIXTURE = FIXTURES_DIR / "sample_state.yaml"
EXPECTED_DIR = FIXTURES_DIR / "phase3b_expected"


def _load_state(tmp_path: Path) -> State:
    raw = yaml.safe_load(STATE_FIXTURE.read_text())
    raw["data_root"] = str(tmp_path)
    raw["backup_dir"] = str(tmp_path / "backups")
    return State(raw)


def _fake_run(_cmd, **_kwargs):
    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    return Result()


def _render_output_tree(tmp_path: Path) -> Path:
    output_root = tmp_path / "rendered"
    state = _load_state(output_root)

    with (
        patch("rakkib.steps.caddy.subprocess.run", side_effect=_fake_run),
        patch("rakkib.steps.postgres.subprocess.run", side_effect=_fake_run),
        patch("rakkib.steps.postgres._wait_for_healthy"),
        patch("rakkib.steps.postgres._apply_sql"),
        patch("rakkib.steps.services.compose_up"),
        patch("rakkib.steps.services._reload_caddy"),
        patch("rakkib.steps.services.subprocess.run", side_effect=_fake_run),
        patch("rakkib.hooks.services.subprocess.run", side_effect=_fake_run),
        patch("rakkib.hooks.services.container_running", return_value=True),
        patch("rakkib.hooks.services.health_check", return_value=True),
    ):
        caddy.run(state)
        postgres.run(state)
        services.run(state)

    return output_root


def _normalize(content: str, output_root: Path) -> str:
    return content.replace(str(output_root), "__DATA_ROOT__")


def test_phase3b_output_snapshot(tmp_path: Path):
    output_root = _render_output_tree(tmp_path)

    expected_files = sorted(path for path in EXPECTED_DIR.rglob("*") if path.is_file())
    assert expected_files

    for expected_path in expected_files:
        relative_path = expected_path.relative_to(EXPECTED_DIR)
        actual_path = output_root / relative_path
        assert actual_path.exists(), f"Missing rendered file: {relative_path}"

        expected_text = expected_path.read_text().rstrip("\n")
        actual_text = _normalize(actual_path.read_text(), output_root).rstrip("\n")
        assert actual_text == expected_text, f"Snapshot mismatch: {relative_path}"
