"""Tests for state management."""

from __future__ import annotations

import pytest

from rakkib.state import State


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
