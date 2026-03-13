"""API key authentication middleware.

Validates Bearer tokens against hashed keys in the database.
"""

from __future__ import annotations

import hashlib
import logging

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("metosim.api.auth")

security = HTTPBearer()


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256 for storage comparison.

    Args:
        api_key: Raw API key string.

    Returns:
        Hex-encoded SHA-256 hash.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """FastAPI dependency that extracts and validates the API key.

    Returns the hashed key for downstream use (e.g. job ownership).

    Raises:
        HTTPException(401): If the key is missing or invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="API key required. Include 'Authorization: Bearer <key>' header.",
        )

    api_key = credentials.credentials
    key_hash = hash_api_key(api_key)

    # TODO: Validate against DB of registered API keys
    # For MVP, accept any non-empty key and use the hash for ownership
    if len(api_key) < 8:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key format.",
        )

    return key_hash
