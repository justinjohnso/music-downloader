"""Shared API key auth guard for backend routes."""

import os
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

API_KEY_ENV = "SPOTIFY_BACKEND_API_KEY"
API_KEY_HEADER = "X-API-Key"


def require_api_key(
    api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None,
) -> None:
    """Validate API key header against backend environment configuration.

    Args:
        api_key: API key from request header.

    Raises:
        HTTPException: If backend key is missing or request key is invalid.
    """
    configured_api_key = os.getenv(API_KEY_ENV)
    if not configured_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Backend API key is not configured.",
        )

    if not api_key or not secrets.compare_digest(api_key, configured_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
