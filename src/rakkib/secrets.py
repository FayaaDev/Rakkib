"""Secret generation helpers.

Generate POSTGRES_PASSWORD, AUTHENTIK_SECRET_KEY, N8N_ENCRYPTION_KEY, etc.
"""

from __future__ import annotations

import secrets
import string

from rakkib.state import State

ALPHANUMERIC = string.ascii_letters + string.digits


def generate_password(length: int = 32) -> str:
    """Return a random alphanumeric password."""
    return "".join(secrets.choice(ALPHANUMERIC) for _ in range(length))


def generate_secret_key(length: int = 50) -> str:
    """Return a random alphanumeric secret key."""
    return "".join(secrets.choice(ALPHANUMERIC) for _ in range(length))


def generate_oidc_client_id() -> str:
    """Return a random 32-char client ID."""
    return generate_password(32)


def generate_oidc_client_secret() -> str:
    """Return a random 64-char client secret."""
    return generate_password(64)


# Mapping of registry env_keys to their generator functions.
# These correspond to the env_keys declared in registry.yaml.
SECRET_GENERATORS: dict[str, callable] = {
    "POSTGRES_PASSWORD": lambda: generate_password(32),
    "NOCODB_DB_PASS": lambda: generate_password(32),
    "AUTHENTIK_DB_PASS": lambda: generate_password(32),
    "N8N_DB_PASS": lambda: generate_password(32),
    "IMMICH_DB_PASSWORD": lambda: generate_password(32),
    "AUTHENTIK_SECRET_KEY": lambda: generate_secret_key(50),
    # 32 alphanumeric chars = ~190 bits of entropy, sufficient for n8n.
    "N8N_ENCRYPTION_KEY": lambda: generate_password(32),
    "NOCODB_OIDC_CLIENT_ID": generate_oidc_client_id,
    "NOCODB_OIDC_CLIENT_SECRET": generate_oidc_client_secret,
    "NOCODB_ADMIN_PASS": lambda: generate_password(32),
    "AUTHENTIK_ADMIN_PASS": lambda: generate_password(32),
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
