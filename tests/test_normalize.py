"""Tests for rakkib.normalize."""

import pytest

from rakkib.normalize import apply_normalize, eval_when, resolve_numeric_aliases
from rakkib.state import State


class TestEvalWhen:
    def test_equality(self):
        state = State({"platform": "linux"})
        assert eval_when("platform == linux", state) is True
        assert eval_when("platform == mac", state) is False

    def test_inequality(self):
        state = State({"platform": "linux"})
        assert eval_when("platform != mac", state) is True
        assert eval_when("platform != linux", state) is False

    def test_boolean_literal(self):
        state = State({"docker_installed": True})
        assert eval_when("docker_installed == true", state) is True
        assert eval_when("docker_installed == false", state) is False

    def test_null_check(self):
        state = State({"tunnel_uuid": None})
        assert eval_when("tunnel_uuid is not null", state) is False
        state.set("tunnel_uuid", "abc")
        assert eval_when("tunnel_uuid is not null", state) is True

    def test_in_list(self):
        state = State({"selected_services": ["n8n", "immich"]})
        assert eval_when("n8n in selected_services", state) is True
        assert eval_when("dbhub in selected_services", state) is False

    def test_and(self):
        state = State({"tunnel_strategy": "new", "accept_browser_login": False})
        assert (
            eval_when(
                "tunnel_strategy == new and accept_browser_login == false", state
            )
            is True
        )
        state.set("accept_browser_login", True)
        assert (
            eval_when(
                "tunnel_strategy == new and accept_browser_login == false", state
            )
            is False
        )

    def test_or(self):
        state = State({"a": "1", "b": "2"})
        assert eval_when("a == 1 or b == 3", state) is True
        assert eval_when("a == 0 or b == 3", state) is False

    def test_bare_key(self):
        state = State({"flag": True})
        assert eval_when("flag", state) is True
        state.set("flag", False)
        assert eval_when("flag", state) is False

    def test_nested_key(self):
        state = State({"cloudflare": {"tunnel_strategy": "new"}})
        assert eval_when("cloudflare.tunnel_strategy == new", state) is True


class TestResolveNumericAliases:
    def test_empty(self):
        assert resolve_numeric_aliases("", {"1": "a"}) == []
        assert resolve_numeric_aliases("   ", {"1": "a"}) == []

    def test_numeric_aliases(self):
        aliases = {"1": "nocodb", "2": "authentik", "3": "homepage"}
        assert resolve_numeric_aliases("1 3", aliases) == ["nocodb", "homepage"]

    def test_mixed(self):
        aliases = {"6": "n8n"}
        assert resolve_numeric_aliases("n8n 6", aliases) == ["n8n", "n8n"]


class TestApplyNormalize:
    def test_lowercase(self):
        assert apply_normalize("LINUX", "lowercase") == "linux"

    def test_dict_map(self):
        mapping = {"x86_64": "amd64", "aarch64": "arm64"}
        assert apply_normalize("x86_64", mapping) == "amd64"
        assert apply_normalize("unknown", mapping) == "unknown"

    def test_dict_with_default(self):
        mapping = {"0": "root", "default": "sudo"}
        assert apply_normalize("0", mapping) == "root"
        assert apply_normalize("1000", mapping) == "sudo"

    def test_first_non_loopback_ipv4(self):
        assert (
            apply_normalize("127.0.0.1 192.168.1.50", "first_non_loopback_ipv4")
            == "192.168.1.50"
        )
        assert (
            apply_normalize("10.0.0.1 127.0.0.1", "first_non_loopback_ipv4")
            == "10.0.0.1"
        )

    def test_first_active_interface_ipv4(self):
        assert apply_normalize("192.168.1.10", "first_active_interface_ipv4") == "192.168.1.10"

    def test_none(self):
        assert apply_normalize("hello", None) == "hello"
