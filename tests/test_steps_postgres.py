"""Tests for Step 4 — PostgreSQL."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rakkib.state import State
from rakkib.steps import postgres


def _make_state(tmp_path: Path) -> State:
    return State(
        {
            "data_root": str(tmp_path),
            "docker_net": "caddy_net",
            "foundation_services": ["nocodb"],
            "selected_services": ["n8n"],
            "secrets": {
                "mode": "generate",
                "values": {
                    "POSTGRES_PASSWORD": None,
                    "NOCODB_DB_PASS": None,
                    "N8N_DB_PASS": None,
                },
            },
        }
    )


def test_postgres_run_renders_env_and_compose(tmp_path):
    state = _make_state(tmp_path)

    with patch("rakkib.steps.postgres._wait_for_healthy"):
        with patch("rakkib.steps.postgres.docker_run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            postgres.run(state)

    postgres_dir = tmp_path / "docker" / "postgres"
    assert (postgres_dir / ".env").exists()
    assert (postgres_dir / "docker-compose.yml").exists()


def test_postgres_run_generates_init_sql(tmp_path):
    state = _make_state(tmp_path)

    with patch("rakkib.steps.postgres._wait_for_healthy"):
        with patch("rakkib.steps.postgres.docker_run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            postgres.run(state)

    sql_path = tmp_path / "docker" / "postgres" / "init-scripts" / "init-services.sql"
    assert sql_path.exists()
    content = sql_path.read_text()
    assert "CREATE ROLE nocodb" in content
    assert "CREATE ROLE n8n" in content
    assert "CREATE DATABASE nocodb_db OWNER nocodb" in content


def test_generate_init_sql_falls_back_to_flat_state_secret(tmp_path):
    state = _make_state(tmp_path)
    state.set("NOCODB_DB_PASS", "flat-nocodb-pass")
    state.set("secrets.values.NOCODB_DB_PASS", None)

    content = postgres._generate_init_sql(state)

    assert "CREATE ROLE nocodb WITH LOGIN PASSWORD 'flat-nocodb-pass';" in content


def test_generate_init_sql_includes_all_selected_db_services(tmp_path):
    state = _make_state(tmp_path)
    state.set("secrets.values.POSTGRES_PASSWORD", "postgres-pass")
    state.set("secrets.values.NOCODB_DB_PASS", "nocodb-pass")
    state.set("secrets.values.N8N_DB_PASS", "n8n-pass")

    content = postgres._generate_init_sql(state)

    assert "CREATE ROLE nocodb WITH LOGIN PASSWORD 'nocodb-pass';" in content
    assert "CREATE DATABASE nocodb_db OWNER nocodb" in content
    assert "CREATE ROLE n8n WITH LOGIN PASSWORD 'n8n-pass';" in content
    assert "CREATE DATABASE n8n_db OWNER n8n" in content


def test_generate_init_sql_raises_when_service_password_missing(tmp_path):
    state = _make_state(tmp_path)
    state.set("secrets.values.NOCODB_DB_PASS", None)
    state.set("NOCODB_DB_PASS", None)
    state.set("secrets.values.N8N_DB_PASS", "n8n-pass")

    with pytest.raises(RuntimeError, match="NOCODB_DB_PASS"):
        postgres._generate_init_sql(state)


def test_postgres_run_merges_existing_env(tmp_path):
    state = _make_state(tmp_path)
    postgres_dir = tmp_path / "docker" / "postgres"
    postgres_dir.mkdir(parents=True)
    (postgres_dir / ".env").write_text("POSTGRES_PASSWORD=keep-me\nPOSTGRES_INITDB_ARGS=--foo\n")

    with patch("rakkib.steps.postgres._wait_for_healthy"):
        with patch("rakkib.steps.postgres.docker_run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            postgres.run(state)

    env_text = (postgres_dir / ".env").read_text()
    assert "POSTGRES_PASSWORD=keep-me" in env_text
    # Newly-generated value should still be present for something not in existing env.
    # But since our .env.example only has POSTGRES_PASSWORD and POSTGRES_INITDB_ARGS,
    # and both existed, they should be preserved.
    assert "POSTGRES_INITDB_ARGS=--foo" in env_text


def test_postgres_run_sets_env_permissions(tmp_path):
    state = _make_state(tmp_path)

    with patch("rakkib.steps.postgres._wait_for_healthy"):
        with patch("rakkib.steps.postgres.docker_run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            postgres.run(state)

    env_path = tmp_path / "docker" / "postgres" / ".env"
    stat = env_path.stat()
    assert stat.st_mode & 0o777 == 0o600


def test_postgres_run_generates_secrets(tmp_path):
    state = _make_state(tmp_path)
    assert state.get("secrets.values.POSTGRES_PASSWORD") is None

    with patch("rakkib.steps.postgres._wait_for_healthy"):
        with patch("rakkib.steps.postgres.docker_run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            postgres.run(state)

    assert state.get("secrets.values.POSTGRES_PASSWORD") is not None
    assert len(state.get("secrets.values.POSTGRES_PASSWORD")) == 32


def test_postgres_run_no_secrets_generate_when_mode_not_generate(tmp_path):
    state = _make_state(tmp_path)
    state.set("secrets.mode", "manual")
    assert state.get("secrets.values.POSTGRES_PASSWORD") is None

    with patch("rakkib.steps.postgres._wait_for_healthy"):
        with patch("rakkib.steps.postgres.docker_run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            postgres.run(state)

    assert state.get("secrets.values.POSTGRES_PASSWORD") is None


def test_postgres_run_compose_up_failure(tmp_path):
    state = _make_state(tmp_path)

    from rakkib.docker import DockerError

    with patch("rakkib.steps.postgres.docker_run") as mock_run:
        mock_run.side_effect = DockerError("compose failed", ["docker", "compose", "up"], 1, "compose failed")
        with pytest.raises(RuntimeError, match="docker compose up failed"):
            postgres.run(state)


class TestWaitForHealthy:
    @patch("rakkib.steps.postgres.docker_run")
    @patch("rakkib.steps.postgres.time")
    def test_returns_when_healthy(self, mock_time, mock_run):
        mock_run.return_value = MagicMock(stdout="healthy\n")
        postgres._wait_for_healthy()
        mock_run.assert_called_once()

    @patch("rakkib.steps.postgres.docker_run")
    @patch("rakkib.steps.postgres.time")
    def test_raises_on_timeout(self, mock_time, mock_run):
        mock_run.return_value = MagicMock(stdout="starting\n")
        with pytest.raises(RuntimeError, match="did not become healthy"):
            postgres._wait_for_healthy(timeout=2)


def test_postgres_verify_success(tmp_path):
    state = _make_state(tmp_path)

    def side_effect(cmd, **kwargs):
        class Result:
            pass

        r = Result()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        if cmd[0] == "ps":
            r.stdout = "postgres"
        return r

    with patch("rakkib.steps.postgres.docker_run") as mock_run:
        mock_run.side_effect = side_effect
        result = postgres.verify(state)

    assert result.ok is True
    assert result.step == "postgres"


def test_postgres_verify_failure_container_missing(tmp_path):
    state = _make_state(tmp_path)

    def side_effect(cmd, **kwargs):
        class Result:
            pass

        r = Result()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    with patch("rakkib.steps.postgres.docker_run") as mock_run:
        mock_run.side_effect = side_effect
        result = postgres.verify(state)

    assert result.ok is False
    assert "not running" in result.message


def test_postgres_verify_failure_pg_isready(tmp_path):
    state = _make_state(tmp_path)

    def side_effect(cmd, **kwargs):
        class Result:
            pass

        r = Result()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        if cmd[0] == "ps":
            r.stdout = "postgres"
        elif cmd[0] == "exec" and "pg_isready" in cmd:
            r.returncode = 1
            r.stderr = "connection refused"
        return r

    with patch("rakkib.steps.postgres.docker_run") as mock_run:
        mock_run.side_effect = side_effect
        result = postgres.verify(state)

    assert result.ok is False
    assert "pg_isready failed" in result.message
