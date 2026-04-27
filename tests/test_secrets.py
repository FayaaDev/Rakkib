"""Tests for secret generation helpers."""

from __future__ import annotations

import pytest

from rakkib.secrets import (
    SECRET_GENERATORS,
    ensure_secrets,
    generate_oidc_client_id,
    generate_oidc_client_secret,
    generate_password,
    generate_secret_key,
)
from rakkib.state import State


def test_generate_password_default_length():
    assert len(generate_password()) == 32


def test_generate_password_custom_length():
    assert len(generate_password(64)) == 64


def test_generate_password_alphanumeric():
    pw = generate_password()
    assert pw.isalnum()


def test_generate_secret_key_default_length():
    assert len(generate_secret_key()) == 50


def test_generate_oidc_client_id_length():
    assert len(generate_oidc_client_id()) == 32


def test_generate_oidc_client_secret_length():
    assert len(generate_oidc_client_secret()) == 64


def test_ensure_secrets_creates_values():
    state = State({})
    ensure_secrets(state)
    values = state.get("secrets.values")
    assert isinstance(values, dict)
    for key in SECRET_GENERATORS:
        assert key in values
        assert values[key] is not None
        assert len(values[key]) > 0


def test_ensure_secrets_fills_none():
    state = State(
        {
            "secrets": {
                "values": {
                    "POSTGRES_PASSWORD": None,
                    "AUTHENTIK_SECRET_KEY": None,
                }
            }
        }
    )
    ensure_secrets(state)
    assert state.get("secrets.values.POSTGRES_PASSWORD") is not None
    assert state.get("secrets.values.AUTHENTIK_SECRET_KEY") is not None


def test_ensure_secrets_preserves_existing():
    state = State(
        {
            "secrets": {
                "values": {
                    "POSTGRES_PASSWORD": "keep-me",
                    "AUTHENTIK_SECRET_KEY": None,
                }
            }
        }
    )
    ensure_secrets(state)
    assert state.get("secrets.values.POSTGRES_PASSWORD") == "keep-me"
    assert state.get("secrets.values.AUTHENTIK_SECRET_KEY") is not None


def test_ensure_secrets_idempotent():
    state = State({})
    ensure_secrets(state)
    first = state.get("secrets.values.POSTGRES_PASSWORD")
    ensure_secrets(state)
    second = state.get("secrets.values.POSTGRES_PASSWORD")
    assert first == second


def test_ensure_secrets_propagates_to_flat_namespace():
    state = State({})
    ensure_secrets(state)
    for key in SECRET_GENERATORS:
        assert state.get(key) == state.get(f"secrets.values.{key}")


def test_ensure_secrets_does_not_overwrite_existing_flat_key():
    state = State({"POSTGRES_PASSWORD": "existing-flat"})
    ensure_secrets(state)
    assert state.get("POSTGRES_PASSWORD") == "existing-flat"
    assert state.get("secrets.values.POSTGRES_PASSWORD") != "existing-flat"
