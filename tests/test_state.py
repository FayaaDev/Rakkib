"""Tests for state management."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from rakkib.state import State, _coerce_compare, _deep_merge, _eval_when


def test_state_get_and_set():
    state = State({})
    state.set("a.b.c", 42)
    assert state.get("a.b.c") == 42
    assert state.get("a.b") == {"c": 42}
    assert state.get("missing") is None
    assert state.get("missing", "default") == "default"


def test_state_has():
    state = State({"x": {"y": None}})
    assert state.has("x.y") is True
    assert state.has("x.z") is False
    assert state.has("a.b.c") is False


def test_state_merge():
    state = State({"a": 1, "b": {"c": 2}})
    state.merge({"b": {"d": 3}, "e": 4})
    assert state.get("a") == 1
    assert state.get("b.c") == 2
    assert state.get("b.d") == 3
    assert state.get("e") == 4


def test_state_is_confirmed():
    assert State({"confirmed": True}).is_confirmed() is True
    assert State({"confirmed": False}).is_confirmed() is False
    assert State({}).is_confirmed() is False


def _phase_1_state() -> dict:
    return {
        "platform": "linux",
        "arch": "amd64",
        "privilege_mode": "sudo",
        "privilege_strategy": "on_demand",
        "docker_installed": True,
        "host_gateway": "172.18.0.1",
    }


def _phase_2_state() -> dict:
    return {
        **_phase_1_state(),
        "server_name": "myserver",
        "domain": "example.com",
        "cloudflare": {"zone_in_cloudflare": True},
        "admin_user": "ubuntu",
        "admin_email": "admin@example.com",
        "lan_ip": "192.168.1.100",
        "tz": "UTC",
        "data_root": "/srv",
        "docker_net": "caddy_net",
        "backup_dir": "/srv/backups",
    }


def _phase_3_state() -> dict:
    return {
        **_phase_2_state(),
        "foundation_services": ["nocodb", "authentik", "homepage", "uptime-kuma", "dockge"],
        "selected_services": ["n8n", "immich"],
        "host_addons": ["vergo_terminal"],
        "subdomains": {
            "nocodb": "nocodb",
            "authentik": "auth",
            "homepage": "home",
            "uptime-kuma": "status",
            "dockge": "dockge",
            "n8n": "n8n",
            "immich": "immich",
        },
    }


def _phase_4_state() -> dict:
    return {
        **_phase_3_state(),
        "cloudflare": {
            "zone_in_cloudflare": True,
            "auth_method": "browser_login",
            "headless": False,
            "tunnel_strategy": "new",
            "tunnel_name": "myserver",
            "ssh_subdomain": "ssh",
            "tunnel_uuid": None,
            "tunnel_creds_host_path": None,
            "tunnel_creds_container_path": None,
        },
    }


def _phase_5_state() -> dict:
    return {
        **_phase_4_state(),
        "secrets": {
            "mode": "generate",
            "n8n_mode": "fresh",
            "values": {
                "POSTGRES_PASSWORD": None,
                "NOCODB_DB_PASS": None,
                "NOCODB_ADMIN_PASS": None,
                "AUTHENTIK_SECRET_KEY": None,
                "AUTHENTIK_DB_PASS": None,
                "AUTHENTIK_ADMIN_PASS": None,
                "N8N_DB_PASS": None,
                "N8N_ENCRYPTION_KEY": None,
                "IMMICH_DB_PASSWORD": None,
                "IMMICH_VERSION": None,
            },
        },
    }


def _phase_6_state() -> dict:
    return {
        **_phase_5_state(),
        "confirmed": True,
    }


def test_resume_phase_empty_state():
    state = State({})
    assert state.resume_phase() == 1
    assert state.is_phase_complete(1) is False


def test_phase_1_complete():
    state = State(_phase_1_state())
    assert state.is_phase_complete(1) is True
    assert state.resume_phase() == 2


def test_phase_2_complete():
    state = State(_phase_2_state())
    assert state.is_phase_complete(1) is True
    assert state.is_phase_complete(2) is True
    assert state.resume_phase() == 3


def test_phase_3_complete():
    state = State(_phase_3_state())
    assert state.is_phase_complete(3) is True
    assert state.resume_phase() == 4


def test_phase_4_complete_existing_tunnel():
    data = _phase_3_state()
    data["cloudflare"] = {
        "zone_in_cloudflare": True,
        "auth_method": "existing_tunnel",
        "headless": None,
        "tunnel_strategy": "existing",
        "tunnel_name": "myserver",
        "ssh_subdomain": "ssh",
        "tunnel_uuid": None,
        "tunnel_creds_host_path": None,
        "tunnel_creds_container_path": None,
    }
    state = State(data)
    assert state.is_phase_complete(4) is True
    assert state.resume_phase() == 5


def test_phase_4_incomplete_missing_tunnel_name():
    data = _phase_3_state()
    data["cloudflare"] = {
        "zone_in_cloudflare": True,
        "auth_method": "browser_login",
        "headless": False,
        "tunnel_strategy": "new",
        # tunnel_name intentionally missing
        "ssh_subdomain": "ssh",
    }
    state = State(data)
    assert state.is_phase_complete(4) is False
    assert state.resume_phase() == 4


def test_phase_5_complete():
    state = State(_phase_5_state())
    assert state.is_phase_complete(5) is True
    assert state.resume_phase() == 6


def test_phase_6_complete():
    state = State(_phase_6_state())
    assert state.is_phase_complete(6) is True
    assert state.resume_phase() == 7


def test_phase_6_incomplete():
    data = _phase_5_state()
    # confirmed intentionally missing
    state = State(data)
    assert state.is_phase_complete(6) is False
    assert state.resume_phase() == 6


def test_phase_skipped_conditional_field():
    # Phase 4 with new tunnel but no headless answered yet.
    data = _phase_3_state()
    data["cloudflare"] = {
        "zone_in_cloudflare": True,
        "tunnel_strategy": "new",
        "tunnel_name": "myserver",
        "ssh_subdomain": "ssh",
    }
    state = State(data)
    # headless/auth_method are required but conditional on tunnel_strategy == new.
    # Since they are not in state, phase 4 is incomplete.
    assert state.is_phase_complete(4) is False
    assert state.resume_phase() == 4


def test_is_phase_complete_unknown_phase():
    state = State({})
    assert state.is_phase_complete(99) is False


def test_state_load_save(tmp_path):
    path = tmp_path / ".fss-state.yaml"
    state = State({"foo": "bar"})
    state.save(path)
    loaded = State.load(path)
    assert loaded.get("foo") == "bar"


def test_state_load_missing_file(tmp_path):
    path = tmp_path / "nonexistent.yaml"
    state = State.load(path)
    assert state.to_dict() == {}


def test_state_load_empty_file(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("")
    state = State.load(path)
    assert state.to_dict() == {}


def test_state_get_traverses_non_dict():
    state = State({"a": "not_a_dict"})
    assert state.get("a.b") is None
    assert state.get("a.b", "default") == "default"


def test_state_has_traverses_non_dict():
    state = State({"a": "not_a_dict"})
    assert state.has("a.b") is False


def test_state_set_overwrites_non_dict_intermediate():
    state = State({"a": "not_a_dict"})
    state.set("a.b.c", 42)
    assert state.get("a.b.c") == 42
    assert state.get("a") == {"b": {"c": 42}}


def test_state_to_dict_is_shallow_copy():
    state = State({"a": {"b": 1}})
    d = state.to_dict()
    d["a"]["b"] = 2
    assert state.get("a.b") == 2
    d["c"] = 3
    assert state.get("c") is None


def test_state_merge_empty():
    state = State({"a": 1})
    state.merge({})
    assert state.get("a") == 1


def test_deep_merge_overwrites_dict_with_scalar():
    base = {"a": {"b": 1}}
    _deep_merge(base, {"a": "scalar"})
    assert base == {"a": "scalar"}


def test_eval_when_empty():
    state = State({})
    assert _eval_when("", state) is True


def test_eval_when_and_conjunction():
    state = State({"a": 1, "b": 2})
    assert _eval_when("a == 1 and b == 2", state) is True
    assert _eval_when("a == 1 and b == 3", state) is False


def test_eval_when_is_not_null():
    state = State({"x": 1, "y": None})
    assert _eval_when("x is not null", state) is True
    assert _eval_when("y is not null", state) is False
    assert _eval_when("z is not null", state) is False


def test_eval_when_is_null():
    state = State({"x": 1, "y": None})
    assert _eval_when("x is null", state) is False
    assert _eval_when("y is null", state) is True
    assert _eval_when("z is null", state) is True


def test_eval_when_in_list():
    state = State({"items": ["a", "b", "c"]})
    assert _eval_when("a in items", state) is True
    assert _eval_when("d in items", state) is False


def test_eval_when_in_not_list():
    state = State({"items": "not_a_list"})
    assert _eval_when("a in items", state) is False


def test_eval_when_equals():
    state = State({"flag": True, "num": 42, "text": "hello"})
    assert _eval_when("flag == true", state) is True
    assert _eval_when("flag == false", state) is False
    assert _eval_when("num == 42", state) is True
    assert _eval_when("text == hello", state) is True


def test_eval_when_not_equals():
    state = State({"flag": True, "num": 42})
    assert _eval_when("flag != false", state) is True
    assert _eval_when("num != 42", state) is False


def test_eval_when_unknown_returns_false():
    state = State({"a": 1})
    assert _eval_when("some random condition", state) is False


def test_coerce_compare_bool():
    assert _coerce_compare(True, "true") is True
    assert _coerce_compare(True, "True") is True
    assert _coerce_compare(False, "false") is True
    assert _coerce_compare(False, "true") is False


def test_coerce_compare_none():
    assert _coerce_compare(None, "none") is True
    assert _coerce_compare(None, "None") is True
    assert _coerce_compare(None, "foo") is False


def test_is_phase_complete_skips_non_required_fields():
    from rakkib.schema import FieldDef, QuestionSchema

    schema = QuestionSchema(
        schema_version=1,
        phase=1,
        fields=[
            FieldDef(id="optional", type="text", required=False, records=["optional"]),
        ],
    )
    with patch("rakkib.state.load_all_schemas", return_value=[schema]):
        state = State({})
        assert state.is_phase_complete(1) is True


def test_is_phase_complete_skips_summary_fields():
    from rakkib.schema import FieldDef, QuestionSchema

    schema = QuestionSchema(
        schema_version=1,
        phase=1,
        fields=[
            FieldDef(id="summary_field", type="summary", records=["summary_field"]),
        ],
    )
    with patch("rakkib.state.load_all_schemas", return_value=[schema]):
        state = State({})
        assert state.is_phase_complete(1) is True


def test_resume_phase_no_schemas():
    with patch("rakkib.state.load_all_schemas", return_value=[]):
        state = State({})
        assert state.resume_phase() == 7
