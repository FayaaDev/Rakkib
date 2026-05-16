"""Helpers for safely emitting PostgreSQL SQL."""

from __future__ import annotations

import re
from typing import Any


_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def postgres_identifier(value: Any, *, field: str = "postgres identifier") -> str:
    """Return a validated PostgreSQL identifier."""
    identifier = str(value)
    if not _IDENTIFIER_RE.fullmatch(identifier):
        raise ValueError(f"Invalid {field}: {identifier!r}")
    return identifier


def postgres_literal(value: Any) -> str:
    """Return *value* as a PostgreSQL dollar-quoted string literal."""
    text = str(value)
    tag = "rakkib"
    index = 0
    while f"${tag}$" in text:
        index += 1
        tag = f"rakkib_{index}"
    return f"${tag}${text}${tag}$"


def validate_registry_postgres_identifiers(registry: dict[str, Any]) -> None:
    """Validate registry-declared PostgreSQL roles and database names."""
    for svc in registry.get("services", []):
        postgres = svc.get("postgres") or {}
        if not postgres:
            continue

        svc_id = svc.get("id", "<unknown>")
        role = postgres.get("role", svc_id)
        db_name = postgres.get("db", role)
        postgres_identifier(role, field=f"postgres role for service {svc_id}")
        postgres_identifier(db_name, field=f"postgres database for service {svc_id}")
