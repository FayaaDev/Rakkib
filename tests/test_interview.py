"""Tests for rakkib.interview."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from rakkib.interview import (
    _enforce_rules,
    _get_default,
    _handle_derived,
    _handle_repeat,
    _handle_secret_group,
    _handle_summary,
    _prompt_confirm,
    _prompt_multi_select,
    _prompt_single_select,
    _prompt_text,
    _record_dict,
    _record_field_value,
    _run_detect,
    _run_field,
    _validate,
    run_interview,
)
from rakkib.schema import FieldDef, QuestionSchema
from rakkib.state import State


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_state() -> State:
    return State({})


@pytest.fixture
def sample_schema() -> QuestionSchema:
    return QuestionSchema(
        schema_version=1,
        phase=3,
        service_catalog={
            "foundation_bundle": [
                {"slug": "nocodb", "default_subdomain": "nocodb"},
                {"slug": "authentik", "default_subdomain": "auth"},
            ],
            "optional_services": [
                {"slug": "n8n", "default_subdomain": "n8n"},
            ],
        },
        rules=[
            {"if_selected": "transfer", "require_confirm": "transfer_public_risk"},
            {"if_selected": "hermes", "requires": {"foundation_services": ["authentik"]}},
        ],
    )


# ---------------------------------------------------------------------------
# run_interview
# ---------------------------------------------------------------------------


class TestRunInterview:
    @patch("rakkib.interview.load_all_schemas")
    @patch("rakkib.interview.Confirm.ask")
    @patch("rakkib.interview._run_phase")
    def test_resumes_at_phase(self, mock_run_phase, mock_confirm, mock_load):
        schema1 = MagicMock(phase=1)
        schema2 = MagicMock(phase=2)
        schema3 = MagicMock(phase=3)
        mock_load.return_value = [schema1, schema2, schema3]

        state = State({"platform": "linux"})
        with patch.object(state, "resume_phase", return_value=2):
            run_interview(state)

        assert mock_run_phase.call_count == 2

    @patch("rakkib.interview.load_all_schemas")
    @patch("rakkib.interview.Confirm.ask", return_value=True)
    @patch("rakkib.interview._run_phase")
    def test_confirmed_reset(self, mock_run_phase, mock_confirm, mock_load):
        schema1 = MagicMock(phase=1)
        mock_load.return_value = [schema1]

        state = State({"confirmed": True})
        run_interview(state)

        mock_confirm.assert_called_once()
        assert mock_run_phase.call_count == 1

    @patch("rakkib.interview.load_all_schemas")
    @patch("rakkib.interview.Confirm.ask", return_value=False)
    @patch("rakkib.interview._run_phase")
    def test_confirmed_keep(self, mock_run_phase, mock_confirm, mock_load):
        schema1 = MagicMock(phase=1)
        mock_load.return_value = [schema1]

        state = State({"confirmed": True})
        with patch.object(state, "resume_phase", return_value=7):
            with patch.object(state, "save") as mock_save:
                run_interview(state)

        mock_confirm.assert_called_once()
        # Since state is confirmed and user doesn't want to reset, resume_phase
        # will return 7 (complete) and no phases run.
        assert mock_run_phase.call_count == 0


# ---------------------------------------------------------------------------
# _run_field
# ---------------------------------------------------------------------------


class TestRunField:
    def test_skip_when_false(self, empty_state):
        field = FieldDef(
            id="test", type="text", prompt="hello", when="platform == mac"
        )
        with patch("rakkib.interview.Prompt.ask") as mock_ask:
            _run_field(field, empty_state)
            mock_ask.assert_not_called()

    def test_derived_field(self, empty_state):
        field = FieldDef(
            id="data_root",
            type="derived",
            derive_from="platform",
            value={"linux": "/srv", "mac": "$HOME/srv"},
            records=["data_root"],
        )
        empty_state.set("platform", "linux")
        _run_field(field, empty_state)
        assert empty_state.get("data_root") == "/srv"

    def test_text_field(self, empty_state):
        field = FieldDef(
            id="server_name",
            type="text",
            prompt="Server name?",
            validate={"pattern": "^[a-z0-9-]+$", "message": "Invalid"},
            records=["server_name"],
        )
        with patch("rakkib.interview.Prompt.ask", return_value="my-server"):
            _run_field(field, empty_state)
        assert empty_state.get("server_name") == "my-server"

    def test_confirm_field_boolean(self, empty_state):
        field = FieldDef(
            id="docker_installed",
            type="confirm",
            prompt="Docker installed?",
            accepted_inputs={"y": True, "n": False},
            records=["docker_installed"],
        )
        with patch("rakkib.interview.Confirm.ask", return_value=True):
            _run_field(field, empty_state)
        assert empty_state.get("docker_installed") is True

    def test_confirm_field_mapped(self, empty_state):
        field = FieldDef(
            id="secrets_mode",
            type="confirm",
            prompt="Generate?",
            accepted_inputs={"y": "generate", "n": "manual"},
            records=["secrets.mode"],
        )
        with patch("rakkib.interview.Prompt.ask", return_value="y"):
            _run_field(field, empty_state)
        assert empty_state.get("secrets.mode") == "generate"

    def test_single_select(self, empty_state):
        field = FieldDef(
            id="platform",
            type="single_select",
            prompt="Platform?",
            canonical_values=["linux", "mac"],
            aliases={"linux": ["linux"], "mac": ["mac", "macos"]},
            records=["platform"],
        )
        with patch("rakkib.interview.Prompt.ask", return_value="macos"):
            _run_field(field, empty_state)
        assert empty_state.get("platform") == "mac"

    def test_multi_select_deselect(self, empty_state):
        field = FieldDef(
            id="foundation_services",
            type="multi_select",
            selection_mode="deselect_from_default",
            prompt="Deselect?",
            canonical_values=["nocodb", "authentik", "homepage"],
            default=["nocodb", "authentik", "homepage"],
            numeric_aliases={"1": "nocodb", "2": "authentik", "3": "homepage"},
            records=["foundation_services"],
        )
        with patch("rakkib.interview.Prompt.ask", return_value="3"):
            _run_field(field, empty_state)
        assert empty_state.get("foundation_services") == ["nocodb", "authentik"]

    def test_multi_select_add(self, empty_state):
        field = FieldDef(
            id="optional_services",
            type="multi_select",
            selection_mode="add_to_empty",
            prompt="Add?",
            canonical_values=["n8n", "dbhub"],
            default=[],
            numeric_aliases={"6": "n8n"},
            records=["selected_services"],
        )
        with patch("rakkib.interview.Prompt.ask", return_value="n8n"):
            _run_field(field, empty_state)
        assert empty_state.get("selected_services") == ["n8n"]

    def test_value_if_true(self, empty_state):
        field = FieldDef(
            id="advanced_api_token",
            type="confirm",
            prompt="API token?",
            accepted_inputs={"y": True, "n": False},
            records=["cloudflare.auth_method"],
            value_if_true={"cloudflare.auth_method": "api_token"},
        )
        with patch("rakkib.interview.Confirm.ask", return_value=True):
            _run_field(field, empty_state)
        assert empty_state.get("cloudflare.auth_method") == "api_token"

    def test_value_if_true_false_does_not_record(self, empty_state):
        field = FieldDef(
            id="advanced_api_token",
            type="confirm",
            prompt="API token?",
            accepted_inputs={"y": True, "n": False},
            records=["cloudflare.auth_method"],
            value_if_true={"cloudflare.auth_method": "api_token"},
        )
        with patch("rakkib.interview.Confirm.ask", return_value=False):
            _run_field(field, empty_state)
        assert empty_state.get("cloudflare.auth_method") is None

    def test_records_empty_uses_id(self, empty_state):
        field = FieldDef(
            id="accept_browser_login",
            type="confirm",
            prompt="Accept?",
            accepted_inputs={"y": True, "n": False},
            records=[],
        )
        with patch("rakkib.interview.Confirm.ask", return_value=True):
            _run_field(field, empty_state)
        assert empty_state.get("accept_browser_login") is True


# ---------------------------------------------------------------------------
# Derived fields
# ---------------------------------------------------------------------------


class TestHandleDerived:
    def test_detect_command(self, empty_state):
        field = FieldDef(
            id="arch",
            type="derived",
            detect={"command": "echo x86_64", "normalize": {"x86_64": "amd64"}},
            records=["arch"],
        )
        _handle_derived(field, empty_state)
        assert empty_state.get("arch") == "amd64"

    def test_detect_platform_specific(self, empty_state):
        field = FieldDef(
            id="lan_ip",
            type="derived",
            detect={"linux": "echo 192.168.1.10"},
            normalize="first_non_loopback_ipv4",
            records=["lan_ip"],
        )
        empty_state.set("platform", "linux")
        _handle_derived(field, empty_state)
        assert empty_state.get("lan_ip") == "192.168.1.10"

    def test_value_platform_keyed(self, empty_state):
        field = FieldDef(
            id="data_root",
            type="derived",
            derive_from="platform",
            value={"linux": "/srv", "mac": "$HOME/srv"},
            records=["data_root"],
        )
        empty_state.set("platform", "mac")
        _handle_derived(field, empty_state)
        assert empty_state.get("data_root") == "$HOME/srv"

    def test_value_state_keyed(self, empty_state):
        field = FieldDef(
            id="existing_tunnel_auth",
            type="derived",
            value={
                "cloudflare.auth_method": "existing_tunnel",
                "cloudflare.headless": None,
            },
            records=["cloudflare.auth_method", "cloudflare.headless"],
        )
        _handle_derived(field, empty_state)
        assert empty_state.get("cloudflare.auth_method") == "existing_tunnel"
        assert empty_state.get("cloudflare.headless") is None

    def test_template_rendering(self, empty_state):
        field = FieldDef(
            id="backup_dir",
            type="derived",
            derive_from="data_root",
            template="{{data_root}}/backups",
            records=["backup_dir"],
        )
        empty_state.set("data_root", "/srv")
        _handle_derived(field, empty_state)
        assert empty_state.get("backup_dir") == "/srv/backups"

    def test_derived_value_override(self, empty_state):
        field = FieldDef(
            id="headless",
            type="derived",
            derived_value={"cloudflare.auth_method": "browser_login"},
            records=["cloudflare.headless", "cloudflare.auth_method"],
        )
        _handle_derived(field, empty_state)
        assert empty_state.get("cloudflare.auth_method") == "browser_login"


class TestRunDetect:
    def test_simple_command(self):
        field = FieldDef(
            id="arch",
            type="derived",
            detect={"command": "echo arm64"},
            records=["arch"],
        )
        state = State({})
        assert _run_detect(field, state) == "arm64"

    def test_normalize_dict(self):
        field = FieldDef(
            id="arch",
            type="derived",
            detect={"command": "echo x86_64", "normalize": {"x86_64": "amd64"}},
            records=["arch"],
        )
        state = State({})
        assert _run_detect(field, state) == "amd64"

    def test_normalize_default_dict(self):
        field = FieldDef(
            id="privilege",
            type="derived",
            detect={
                "command": "echo 1000",
                "normalize": {
                    "0": {"privilege_mode": "root"},
                    "default": {"privilege_mode": "sudo"},
                },
            },
            records=["privilege_mode"],
        )
        state = State({})
        result = _run_detect(field, state)
        assert result == {"privilege_mode": "sudo"}

    def test_field_level_normalize(self):
        field = FieldDef(
            id="lan_ip",
            type="derived",
            detect={"command": "echo 127.0.0.1 10.0.0.5"},
            normalize="first_non_loopback_ipv4",
            records=["lan_ip"],
        )
        state = State({})
        assert _run_detect(field, state) == "10.0.0.5"


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------


class TestPromptText:
    def test_basic(self):
        field = FieldDef(id="name", type="text", prompt="Name?")
        with patch("rakkib.interview.Prompt.ask", return_value="alice"):
            assert _prompt_text(field, State({})) == "alice"

    def test_default_used(self):
        field = FieldDef(id="name", type="text", prompt="Name?", default="bob")
        with patch("rakkib.interview.Prompt.ask", return_value="") as mock_ask:
            result = _prompt_text(field, State({}))
            mock_ask.assert_called_once_with("Name?", default="bob")
            assert result == "bob"

    def test_validation_re_prompt(self):
        field = FieldDef(
            id="name",
            type="text",
            prompt="Name?",
            validate={"pattern": "^[a-z]+$", "message": "lowercase only"},
        )
        with patch(
            "rakkib.interview.Prompt.ask", side_effect=["Alice", "alice"]
        ):
            assert _prompt_text(field, State({})) == "alice"


class TestPromptConfirm:
    def test_boolean_confirm(self):
        field = FieldDef(
            id="flag", type="confirm", prompt="Flag?", accepted_inputs={"y": True, "n": False}
        )
        with patch("rakkib.interview.Confirm.ask", return_value=True):
            assert _prompt_confirm(field, State({})) is True

    def test_mapped_confirm(self):
        field = FieldDef(
            id="mode",
            type="confirm",
            prompt="Mode?",
            accepted_inputs={"y": "generate", "n": "manual"},
        )
        with patch("rakkib.interview.Prompt.ask", return_value="y"):
            result = _prompt_confirm(field, State({}))
            assert result == "generate"

    def test_mapped_confirm_invalid_then_valid(self):
        field = FieldDef(
            id="mode",
            type="confirm",
            prompt="Mode?",
            accepted_inputs={"y": "generate", "n": "manual"},
        )
        with patch(
            "rakkib.interview.Prompt.ask", side_effect=["x", "n"]
        ):
            result = _prompt_confirm(field, State({}))
            assert result == "manual"


class TestPromptSingleSelect:
    def test_alias(self):
        field = FieldDef(
            id="platform",
            type="single_select",
            prompt="Platform?",
            canonical_values=["linux", "mac"],
            aliases={"mac": ["mac", "macos"]},
        )
        with patch("rakkib.interview.Prompt.ask", return_value="macos"):
            assert _prompt_single_select(field, State({})) == "mac"

    def test_canonical(self):
        field = FieldDef(
            id="platform",
            type="single_select",
            prompt="Platform?",
            canonical_values=["linux", "mac"],
        )
        with patch("rakkib.interview.Prompt.ask", return_value="linux"):
            assert _prompt_single_select(field, State({})) == "linux"

    def test_invalid_then_valid(self):
        field = FieldDef(
            id="platform",
            type="single_select",
            prompt="Platform?",
            canonical_values=["linux", "mac"],
        )
        with patch(
            "rakkib.interview.Prompt.ask", side_effect=["windows", "mac"]
        ):
            assert _prompt_single_select(field, State({})) == "mac"


class TestPromptMultiSelect:
    def test_deselect(self):
        field = FieldDef(
            id="foundation",
            type="multi_select",
            selection_mode="deselect_from_default",
            prompt="Deselect?",
            canonical_values=["a", "b", "c"],
            default=["a", "b", "c"],
            numeric_aliases={"1": "a", "2": "b", "3": "c"},
        )
        with patch("rakkib.interview.Prompt.ask", return_value="3"):
            assert _prompt_multi_select(field, State({})) == ["a", "b"]

    def test_add_to_empty(self):
        field = FieldDef(
            id="optional",
            type="multi_select",
            selection_mode="add_to_empty",
            prompt="Add?",
            canonical_values=["x", "y"],
            default=[],
            numeric_aliases={"1": "x"},
        )
        with patch("rakkib.interview.Prompt.ask", return_value="x y"):
            assert _prompt_multi_select(field, State({})) == ["x", "y"]

    def test_empty_input_uses_default(self):
        field = FieldDef(
            id="foundation",
            type="multi_select",
            selection_mode="deselect_from_default",
            prompt="Deselect?",
            canonical_values=["a", "b"],
            default=["a", "b"],
        )
        with patch("rakkib.interview.Prompt.ask", return_value=""):
            assert _prompt_multi_select(field, State({})) == ["a", "b"]


# ---------------------------------------------------------------------------
# Special handlers
# ---------------------------------------------------------------------------


class TestHandleSecretGroup:
    def test_prompts_for_each_entry(self):
        field = FieldDef(
            id="secrets",
            type="secret_group",
            entries=[
                {"key": "POSTGRES_PASSWORD", "when": "always"},
                {"key": "NOCODB_DB_PASS", "when": "nocodb in foundation_services"},
            ],
        )
        state = State({"foundation_services": ["nocodb"]})
        with patch(
            "rakkib.interview.Prompt.ask", side_effect=["secret1", "secret2"]
        ):
            _handle_secret_group(field, state)
        assert state.get("secrets.values.POSTGRES_PASSWORD") == "secret1"
        assert state.get("secrets.values.NOCODB_DB_PASS") == "secret2"

    def test_skips_when_condition_false(self):
        field = FieldDef(
            id="secrets",
            type="secret_group",
            entries=[
                {"key": "NOCODB_DB_PASS", "when": "nocodb in foundation_services"},
            ],
        )
        state = State({"foundation_services": []})
        with patch("rakkib.interview.Prompt.ask") as mock_ask:
            _handle_secret_group(field, state)
            mock_ask.assert_not_called()

    def test_rejects_empty(self):
        field = FieldDef(
            id="secrets",
            type="secret_group",
            entries=[{"key": "POSTGRES_PASSWORD", "when": "always"}],
        )
        state = State({})
        with patch(
            "rakkib.interview.Prompt.ask", side_effect=["", "valid"]
        ):
            _handle_secret_group(field, state)
        assert state.get("secrets.values.POSTGRES_PASSWORD") == "valid"


class TestHandleSummary:
    def test_prints_summary(self):
        field = FieldDef(
            id="summary",
            type="summary",
            summary_fields=["platform", "server_name"],
        )
        state = State({"platform": "linux", "server_name": "test"})
        with patch("rakkib.interview.console.print") as mock_print:
            _handle_summary(field, state)
            calls = [str(c) for c in mock_print.call_args_list]
            assert any("linux" in c for c in calls)
            assert any("test" in c for c in calls)


class TestHandleRepeat:
    def test_default_subdomains_no_customize(self, sample_schema, empty_state):
        field = FieldDef(
            id="service_subdomain",
            type="text",
            repeat_for="selected_service_slugs",
            prompt_template="Subdomain for <service>? [default: <default>]",
            records=["subdomains"],
        )
        empty_state.set("foundation_services", ["nocodb", "authentik"])
        empty_state.set("selected_services", ["n8n"])
        empty_state.set("customize_subdomains", False)
        _handle_repeat(field, empty_state, sample_schema)
        assert empty_state.get("subdomains.nocodb") == "nocodb"
        assert empty_state.get("subdomains.authentik") == "auth"
        assert empty_state.get("subdomains.n8n") == "n8n"

    def test_customize_subdomains(self, sample_schema, empty_state):
        field = FieldDef(
            id="service_subdomain",
            type="text",
            repeat_for="selected_service_slugs",
            prompt_template="Subdomain for <service>? [default: <default>]",
            validate={"pattern": "^[a-z0-9-]+$", "message": "Invalid"},
            records=["subdomains"],
        )
        empty_state.set("foundation_services", ["nocodb"])
        empty_state.set("customize_subdomains", True)
        with patch("rakkib.interview.Prompt.ask", return_value="db"):
            _handle_repeat(field, empty_state, sample_schema)
        assert empty_state.get("subdomains.nocodb") == "db"


# ---------------------------------------------------------------------------
# Rules enforcement
# ---------------------------------------------------------------------------


class TestEnforceRules:
    def test_transfer_warn_and_remove(self, sample_schema):
        state = State({"selected_services": ["transfer"]})
        with patch("rakkib.interview.Confirm.ask", return_value=False):
            _enforce_rules(sample_schema, state)
        assert state.get("selected_services") == []

    def test_transfer_accepted(self, sample_schema):
        state = State({"selected_services": ["transfer"]})
        with patch("rakkib.interview.Confirm.ask", return_value=True):
            _enforce_rules(sample_schema, state)
        assert state.get("selected_services") == ["transfer"]

    def test_hermes_adds_authentik(self, sample_schema):
        state = State({
            "selected_services": ["hermes"],
            "foundation_services": ["nocodb"],
        })
        with patch("rakkib.interview.console.print"):
            _enforce_rules(sample_schema, state)
        assert "authentik" in state.get("foundation_services")


# ---------------------------------------------------------------------------
# Defaults & validation
# ---------------------------------------------------------------------------


class TestGetDefault:
    def test_default_from_state(self):
        field = FieldDef(id="x", type="text", default_from_state="server_name")
        state = State({"server_name": "srv"})
        assert _get_default(field, state) == "srv"

    def test_default_from_host_command(self):
        field = FieldDef(id="x", type="text", default_from_host="echo hello")
        assert _get_default(field, State({})) == "hello"

    def test_default_from_host_dict_linux(self):
        field = FieldDef(
            id="x", type="text", default_from_host={"linux": "echo linux_user"}
        )
        state = State({"platform": "linux"})
        assert _get_default(field, state) == "linux_user"

    def test_default_from_host_sudo_user(self, monkeypatch):
        monkeypatch.setenv("SUDO_USER", "admin")
        field = FieldDef(
            id="x",
            type="text",
            default_from_host={"linux": "id -un", "sudo_linux": "SUDO_USER"},
        )
        state = State({"platform": "linux"})
        assert _get_default(field, state) == "admin"

    def test_plain_default(self):
        field = FieldDef(id="x", type="text", default="foo")
        assert _get_default(field, State({})) == "foo"


class TestValidate:
    def test_non_empty(self):
        field = FieldDef(
            id="x", type="text", validate={"non_empty": True, "message": "Required"}
        )
        assert _validate("hello", field) is True
        assert _validate("", field) is False

    def test_pattern(self):
        field = FieldDef(
            id="x",
            type="text",
            validate={"pattern": "^[a-z]+$", "message": "letters only"},
        )
        assert _validate("abc", field) is True
        assert _validate("ABC", field) is False

    def test_string_pattern(self):
        field = FieldDef(id="x", type="text", validate="^[0-9]+$")
        assert _validate("123", field) is True
        assert _validate("abc", field) is False

    def test_no_validate(self):
        field = FieldDef(id="x", type="text")
        assert _validate("anything", field) is True


# ---------------------------------------------------------------------------
# Recording helpers
# ---------------------------------------------------------------------------


class TestRecordFieldValue:
    def test_basic_record(self, empty_state):
        field = FieldDef(id="x", type="text", records=["a", "b"])
        _record_field_value(field, "val", empty_state)
        assert empty_state.get("a") == "val"
        assert empty_state.get("b") == "val"

    def test_derived_value_override(self, empty_state):
        field = FieldDef(
            id="x",
            type="text",
            records=["a", "b"],
            derived_value={"b": "override"},
        )
        _record_field_value(field, "val", empty_state)
        assert empty_state.get("a") == "val"
        assert empty_state.get("b") == "override"

    def test_empty_records_uses_id(self, empty_state):
        field = FieldDef(id="customize_subdomains", type="confirm", records=[])
        _record_field_value(field, True, empty_state)
        assert empty_state.get("customize_subdomains") is True


class TestRecordDict:
    def test_records_dict(self, empty_state):
        _record_dict({"a.b": "1", "c": "2"}, empty_state)
        assert empty_state.get("a.b") == "1"
        assert empty_state.get("c") == "2"
