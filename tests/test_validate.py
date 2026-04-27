"""Tests for validation and normalization utilities."""

from __future__ import annotations

import pytest

from rakkib.schema import FieldDef
from rakkib.validate import (
    normalize_value,
    validate_domain,
    validate_text,
    validate_uuid,
)


def test_validate_text_non_empty():
    assert validate_text("hello", {"non_empty": True}) is None
    assert validate_text("", {"non_empty": True}) == "Value must not be empty."
    assert validate_text("  ", {"non_empty": True}) == "Value must not be empty."


def test_validate_text_pattern():
    rules = {"pattern": r"^[a-z]+$", "message": "Lowercase only."}
    assert validate_text("abc", rules) is None
    assert validate_text("ABC", rules) == "Lowercase only."


def test_validate_text_non_empty_with_message():
    rules = {"non_empty": True, "message": "Required."}
    assert validate_text("", rules) == "Required."


def test_validate_text_no_rules():
    assert validate_text("anything", {}) is None


def test_validate_text_non_string():
    assert validate_text(123, {"non_empty": True}) == "Value must be a string."


def test_validate_domain_valid():
    assert validate_domain("example.com") is None
    assert validate_domain("sub.example.co.uk") is None


def test_validate_domain_with_scheme():
    assert validate_domain("https://example.com") is not None
    assert validate_domain("http://example.com") is not None


def test_validate_domain_no_dot():
    assert validate_domain("example") is not None


def test_validate_domain_non_string():
    assert validate_domain(123) is not None


def test_validate_uuid_valid():
    assert validate_uuid("123e4567-e89b-12d3-a456-426614174000") is None


def test_validate_uuid_invalid():
    assert validate_uuid("not-a-uuid") is not None
    assert validate_uuid("123e4567e89b12d3a456426614174000") is not None


def test_normalize_value_lowercase():
    field = FieldDef(id="x", type="text", normalize="lowercase")
    assert normalize_value("LINUX", field) == "linux"
    assert normalize_value("Linux", field) == "linux"


def test_normalize_value_aliases():
    field = FieldDef(
        id="x",
        type="single_select",
        aliases={
            "mac": ["mac", "macos", "osx", "darwin"],
            "linux": ["linux"],
        },
    )
    assert normalize_value("osx", field) == "mac"
    assert normalize_value("Darwin", field) == "mac"
    assert normalize_value("linux", field) == "linux"
    assert normalize_value("unknown", field) == "unknown"


def test_normalize_value_accepted_inputs():
    field = FieldDef(
        id="x",
        type="confirm",
        accepted_inputs={
            "y": True,
            "n": False,
            "yes": True,
            "no": False,
        },
    )
    assert normalize_value("y", field) is True
    assert normalize_value("N", field) is False
    assert normalize_value("YES", field) is True
    assert normalize_value("maybe", field) == "maybe"


def test_normalize_value_numeric_aliases():
    field = FieldDef(
        id="x",
        type="multi_select",
        numeric_aliases={"1": "nocodb", "2": "authentik"},
    )
    assert normalize_value("1", field) == "nocodb"
    assert normalize_value("2", field) == "authentik"
    assert normalize_value("3", field) == "3"


def test_normalize_value_none():
    field = FieldDef(id="x", type="text")
    assert normalize_value(None, field) is None


def test_normalize_value_no_rules():
    field = FieldDef(id="x", type="text")
    assert normalize_value("unchanged", field) == "unchanged"


def test_normalize_value_priority_aliases_over_lowercase():
    # aliases run after lowercase normalization, so "Darwin" -> lowercase -> "darwin" -> alias -> "mac"
    field = FieldDef(
        id="x",
        type="single_select",
        normalize="lowercase",
        aliases={"mac": ["mac", "darwin"]},
    )
    assert normalize_value("Darwin", field) == "mac"
