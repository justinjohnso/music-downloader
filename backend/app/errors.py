"""Error helpers for the backend Spotify resolve endpoint."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.spotify_links import (
    SPOTIFY_URI_PREFIX,
    SPOTIFY_URL_PREFIX,
    SUPPORTED_SPOTIFY_TYPES,
)
from app.spotify_service import (
    InvalidSpotifyLinkError,
    SpotifyCredentialsError,
    SpotifyLookupError,
)


class UnsupportedSpotifyLinkTypeError(ValueError):
    """Raised when a Spotify URL/URI type is not supported."""


def validate_spotify_link(spotify_link: str) -> None:
    """Validate link shape and distinguish invalid vs unsupported types."""
    if spotify_link.startswith(SPOTIFY_URI_PREFIX):
        parts = spotify_link.split(":")
        if len(parts) < 3 or not parts[2]:
            raise InvalidSpotifyLinkError("Invalid Spotify URI format.")

        if parts[1] not in SUPPORTED_SPOTIFY_TYPES:
            raise UnsupportedSpotifyLinkTypeError(
                "Unsupported Spotify link type. Only track and playlist are supported."
            )
        return

    if spotify_link.startswith(SPOTIFY_URL_PREFIX):
        base_url = spotify_link.split("?")[0]
        parts = base_url.split("/")
        if len(parts) < 5 or not parts[4]:
            raise InvalidSpotifyLinkError("Invalid Spotify URL format.")

        if parts[3] not in SUPPORTED_SPOTIFY_TYPES:
            raise UnsupportedSpotifyLinkTypeError(
                "Unsupported Spotify link type. Only track and playlist are supported."
            )
        return

    raise InvalidSpotifyLinkError("Invalid Spotify link format.")


def map_error_to_http_exception(error: Exception) -> HTTPException:
    """Map domain/service errors to explicit HTTP responses."""
    if isinstance(error, UnsupportedSpotifyLinkTypeError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        )

    if isinstance(error, InvalidSpotifyLinkError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    if isinstance(error, SpotifyLookupError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        )

    if isinstance(error, SpotifyCredentialsError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error.",
    )


def get_error_code(status_code: int) -> str | None:
    """Map HTTP status codes to shared error code values."""
    if status_code in (
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ):
        return "invalid_spotify_link"

    if status_code == status.HTTP_502_BAD_GATEWAY:
        return "spotify_error"

    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        return "internal_error"

    return None
