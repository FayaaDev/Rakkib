"""Validation and normalization utilities."""

from __future__ import annotations

import re
from typing import Any

from rakkib.schema import FieldDef


def validate_text(value: str, rules: dict) -> str | None:
    """Validate a text value against rules.

    Returns an error message if invalid, or None if valid.
    """
    if not isinstance(value, str):
        return "Value must be a string."

    if rules.get("non_empty"):
        if not value.strip():
            return rules.get("message", "Value must not be empty.")

    pattern = rules.get("pattern")
    if pattern:
        if not re.search(pattern, value):
            return rules.get("message", "Invalid value.")

    return None


def validate_domain(value: str) -> str | None:
    """Validate a bare domain name (no scheme, must contain a dot)."""
    if not isinstance(value, str):
        return "Value must be a string."
    if value.startswith(("http://", "https://")):
        return "Use a bare domain like example.com, without http:// or https://."
    if "." not in value:
        return "Domain must contain at least one dot."
    return None


def validate_uuid(value: str) -> str | None:
    """Validate a UUID string."""
    if not isinstance(value, str):
        return "Value must be a string."
    pattern = (
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )
    if not re.match(pattern, value):
        return "Enter a valid UUID like 123e4567-e89b-12d3-a456-426614174000."
    return None


def normalize_value(value: Any, field: FieldDef) -> Any:
    """Normalize a single value using field rules (aliases, accepted_inputs, lowercase, etc.)."""
    if value is None:
        return None

    # Handle string normalization first
    if isinstance(value, str):
        # lowercase normalization
        if field.normalize == "lowercase":
            value = value.lower()

        # aliases: map alias -> canonical
        if field.aliases:
            lowered = value.lower()
            for canonical, aliases in field.aliases.items():
                if lowered in [a.lower() for a in aliases]:
                    return canonical

        # accepted_inputs: map raw input -> normalized value
        if field.accepted_inputs:
            lowered = value.lower()
            for k, v in field.accepted_inputs.items():
                if k.lower() == lowered:
                    return v

        # numeric_aliases: map "1" -> canonical
        if field.numeric_aliases:
            if value in field.numeric_aliases:
                return field.numeric_aliases[value]

    return value
