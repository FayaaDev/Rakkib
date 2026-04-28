"""Normalization helpers for when-expressions, aliases, and value transforms."""

from __future__ import annotations

import ipaddress
import re
from typing import Any

from rakkib.state import State

_RX_IN = re.compile(r"^(.+?)\s+in\s+(.+)$")
_RX_IS_NOT_NULL = re.compile(r"^(.+?)\s+is\s+not\s+null$")
_RX_EQ = re.compile(r"^(.+?)\s*==\s*(.+)$")
_RX_NEQ = re.compile(r"^(.+?)\s*!=\s*(.+)$")


def eval_when(when: str, state: State) -> bool:
    """Evaluate simple when expressions against current state.

    Supported forms:
      - key == value
      - key != value
      - value in key
      - key is not null
      - expr1 and expr2
      - expr1 or expr2
    """
    when = when.strip()

    # Split by ' or ' first (lowest precedence)
    or_parts = [p.strip() for p in when.split(" or ")]
    if len(or_parts) > 1:
        return any(eval_when(p, state) for p in or_parts)

    # Split by ' and '
    and_parts = [p.strip() for p in when.split(" and ")]
    if len(and_parts) > 1:
        return all(eval_when(p, state) for p in and_parts)

    # Single clause ---------------------------------------------------------

    # value in key
    m = _RX_IN.match(when)
    if m:
        value = m.group(1).strip()
        key = m.group(2).strip()
        state_value = state.get(key)
        if isinstance(state_value, list):
            return value in state_value
        return False

    # key is not null
    m = _RX_IS_NOT_NULL.match(when)
    if m:
        key = m.group(1).strip()
        return state.get(key) is not None

    # key == value
    m = _RX_EQ.match(when)
    if m:
        key = m.group(1).strip()
        expected = m.group(2).strip()
        actual = state.get(key)
        if expected == "true":
            return actual is True
        if expected == "false":
            return actual is False
        if expected == "null":
            return actual is None
        return str(actual) == expected

    # key != value
    m = _RX_NEQ.match(when)
    if m:
        return not eval_when(f"{m.group(1).strip()} == {m.group(2).strip()}", state)

    # Bare key (truthiness)
    return bool(state.get(when))


def resolve_numeric_aliases(input_str: str, aliases: dict[str, str]) -> list[str]:
    """Resolve space-separated input, mapping numeric aliases to canonical values."""
    if not input_str or not input_str.strip():
        return []
    parts = input_str.strip().split()
    result: list[str] = []
    for part in parts:
        result.append(aliases.get(part, part))
    return result


def apply_normalize(value: str, normalize: str | dict[str, Any] | None) -> Any:
    """Apply normalization to a raw string value."""
    if normalize is None:
        return value

    if isinstance(normalize, dict):
        return normalize.get(value, normalize.get("default", value))

    if normalize == "lowercase":
        return value.lower()

    if normalize == "first_non_loopback_ipv4":
        for token in value.split():
            token = token.strip()
            if not token:
                continue
            try:
                ip = ipaddress.ip_address(token)
                if not ip.is_loopback and ip.version == 4:
                    return str(ip)
            except ValueError:
                continue
        return value.strip()

    if normalize == "first_active_interface_ipv4":
        try:
            ip = ipaddress.ip_address(value.strip())
            return str(ip)
        except ValueError:
            return value.strip()

    return value
