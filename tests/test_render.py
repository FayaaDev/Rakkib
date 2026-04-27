"""Tests for template rendering."""

from __future__ import annotations

import pytest

from rakkib.render import flatten_state, render_file, render_string, render_text, render_tree
from rakkib.state import State


def test_flatten_state_basic():
    state = State({"domain": "example.com", "port": 8080})
    flat = flatten_state(state)
    assert flat["DOMAIN"] == "example.com"
    assert flat["PORT"] == "8080"


def test_flatten_state_nested():
    state = State({"cloudflare": {"tunnel_uuid": "abc123"}})
    flat = flatten_state(state)
    assert flat["CLOUDFLARE.TUNNEL_UUID"] == "abc123"


def test_flatten_state_list():
    state = State({"services": ["caddy", "postgres"]})
    flat = flatten_state(state)
    assert flat["SERVICES"] == "caddy\npostgres"


def test_flatten_state_none():
    state = State({"empty": None})
    flat = flatten_state(state)
    assert flat["EMPTY"] == ""


def test_render_string_simple():
    result = render_string("Hello {{NAME}}!", {"NAME": "World"})
    assert result == "Hello World!"


def test_render_string_jinja_style():
    result = render_string("Hello {{ NAME }}!", {"NAME": "World"})
    assert result == "Hello World!"


def test_render_string_missing_placeholder():
    """Missing placeholders are left as-is using DebugUndefined."""
    result = render_string("Hello {{ MISSING }}!", {"NAME": "World"})
    assert result == "Hello {{ MISSING }}!"


def test_render_text():
    state = State({"greeting": "Hi", "target": "there"})
    result = render_text("{{GREETING}} {{TARGET}}", state)
    assert result == "Hi there"


def test_render_file(tmp_path):
    src = tmp_path / "test.txt.tmpl"
    dst = tmp_path / "test.txt"
    src.write_text("domain={{DOMAIN}}")

    state = State({"domain": "example.com"})
    render_file(src, dst, state)

    assert dst.read_text() == "domain=example.com"


def test_render_tree(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "sub").mkdir(parents=True)

    (src / "a.txt.tmpl").write_text("{{A}}")
    (src / "sub" / "b.txt.tmpl").write_text("{{B}}")
    (src / "skip.txt").write_text("static")

    state = State({"a": "alpha", "b": "beta"})
    render_tree(src, dst, state)

    assert (dst / "a.txt").read_text() == "alpha"
    assert (dst / "sub" / "b.txt").read_text() == "beta"
    assert not (dst / "skip.txt").exists()


def test_flatten_state_deeply_nested():
    state = State({"a": {"b": {"c": "deep"}}})
    flat = flatten_state(state)
    assert flat["A.B.C"] == "deep"


def test_flatten_state_mixed_list():
    state = State({"items": [1, True, None, "str"]})
    flat = flatten_state(state)
    # List items use str(x) uniformly; scalar None becomes "" but list None becomes "None"
    assert flat["ITEMS"] == "1\nTrue\nNone\nstr"


def test_flatten_state_empty():
    state = State({})
    flat = flatten_state(state)
    assert flat == {}


def test_render_file_missing_parent_dir(tmp_path):
    src = tmp_path / "src.txt.tmpl"
    src.write_text("{{X}}")
    dst = tmp_path / "nonexistent" / "dst.txt"
    state = State({"x": "value"})
    with pytest.raises(FileNotFoundError):
        render_file(src, dst, state)


def test_render_tree_empty_source(tmp_path):
    src = tmp_path / "empty_src"
    src.mkdir()
    dst = tmp_path / "empty_dst"
    render_tree(src, dst, State({}))
    assert not dst.exists() or list(dst.iterdir()) == []


def test_render_text_with_underscore_key():
    state = State({"tunnel_uuid": "abc-123"})
    result = render_text("UUID={{TUNNEL_UUID}}", state)
    assert result == "UUID=abc-123"
