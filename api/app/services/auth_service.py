"""Authentication service — API key validation and management."""

from __future__ import annotations

import hashlib
import secrets
from typing import Optional


def generate_api_key(prefix: str = "mts") -> str:
    """Generate a new API key.

    Args:
        prefix: Key prefix for identification.

    Returns:
        API key string (e.g. 'mts_abc123def456...').
    """
    raw = secrets.token_hex(32)
    return f"{prefix}_{raw}"


def hash_key(api_key: str) -> str:
    """Hash an API key for storage.

    Args:
        api_key: Raw API key.

    Returns:
        SHA-256 hex digest.
    """
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


async def validate_key(api_key_hash: str) -> bool:
    """Validate a hashed API key against the database.

    Args:
        api_key_hash: SHA-256 hash of the key to validate.

    Returns:
        True if the key is valid and active.
    """
    # TODO: Query database for active key matching this hash
    # For MVP, accept all properly formatted keys
    return len(api_key_hash) == 64
