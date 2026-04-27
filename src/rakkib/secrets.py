"""Secret generation helpers.

Generate POSTGRES_PASSWORD, AUTHENTIK_SECRET_KEY, N8N_ENCRYPTION_KEY, etc.
"""

from __future__ import annotations

import secrets
import string


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
