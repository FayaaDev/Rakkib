"""Secret generation helpers.

Generate POSTGRES_PASSWORD, N8N_ENCRYPTION_KEY, etc.
"""

from __future__ import annotations

import base64
import hmac
import os
import random
import string
from typing import Callable

from rakkib.state import State

ALPHANUMERIC = string.ascii_letters + string.digits
_SYSTEM_RANDOM = random.SystemRandom()


def generate_password(length: int = 32) -> str:
    """Return a random alphanumeric password."""
    return "".join(_SYSTEM_RANDOM.choice(ALPHANUMERIC) for _ in range(length))


def generate_secret_key(length: int = 50) -> str:
    """Return a random alphanumeric secret key."""
    return "".join(_SYSTEM_RANDOM.choice(ALPHANUMERIC) for _ in range(length))


def generate_hex_key(length: int = 64) -> str:
    """Return a random lowercase hexadecimal secret key."""
    return os.urandom((length + 1) // 2).hex()[:length]


def token_urlsafe(nbytes: int = 32) -> str:
    """Return a URL-safe random token without importing the stdlib secrets module."""
    return base64.urlsafe_b64encode(os.urandom(nbytes)).rstrip(b"=").decode("ascii")


def compare_digest(a: str | bytes, b: str | bytes) -> bool:
    """Return a constant-time comparison result."""
    return hmac.compare_digest(a, b)


FACTORIES: dict[str, Callable[..., str]] = {
    "password": generate_password,
    "secret_key": generate_secret_key,
    "hex_key": generate_hex_key,
}


# Mapping of registry env_keys to their generator functions.
# These correspond to the env_keys declared in registry.yaml.
SECRET_GENERATORS: dict[str, Callable[[], str]] = {
    "POSTGRES_PASSWORD": lambda: generate_password(32),
    "NOCODB_DB_PASS": lambda: generate_password(32),
    "N8N_DB_PASS": lambda: generate_password(32),
    "IMMICH_DB_PASSWORD": lambda: generate_password(32),
    # 32 alphanumeric chars = ~190 bits of entropy, sufficient for n8n.
    "N8N_ENCRYPTION_KEY": lambda: generate_password(32),
    "NOCODB_ADMIN_PASS": lambda: generate_password(32),
}


def ensure_secrets(state: State) -> None:
    """Read ``secrets.values`` from *state*, generate any missing or ``None`` entries, and write back.

    Only keys listed in :data:`SECRET_GENERATORS` are touched.  Existing
    non-None values are preserved so that re-running the step is safe.
    """
    values = state.get("secrets.values")
    if not isinstance(values, dict):
        values = {}

    changed = False
    for key, generator in SECRET_GENERATORS.items():
        if values.get(key) is None:
            values[key] = generator()
            changed = True

    if changed:
        state.set("secrets.values", values)

    # Propagate nested secrets to flat namespace so downstream steps
    # (e.g. services._generate_missing_secrets) find them via state.has()/state.get()
    # instead of generating divergent passwords.
    for key, val in (values or {}).items():
        if not state.has(key):
            state.set(key, val)
