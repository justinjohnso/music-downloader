"""Spotify URL/URI parsing utilities shared by backend services."""

from typing import Literal

SPOTIFY_URL_PREFIX = "https://open.spotify.com/"
SPOTIFY_URI_PREFIX = "spotify:"
SUPPORTED_SPOTIFY_TYPES = {"track", "playlist"}

SpotifyItemType = Literal["track", "playlist"]


def is_spotify_link(link: str) -> bool:
    """Check if the provided string is a Spotify URL or URI."""
    return link.startswith(SPOTIFY_URL_PREFIX) or link.startswith(SPOTIFY_URI_PREFIX)


def extract_spotify_info(link: str) -> tuple[str, SpotifyItemType]:
    """Extract Spotify item ID and item type from a URL or URI."""
    if link.startswith(SPOTIFY_URI_PREFIX):
        parts = link.split(":")
        if len(parts) >= 3 and parts[1] in SUPPORTED_SPOTIFY_TYPES and parts[2]:
            return parts[2], parts[1]

    elif link.startswith(SPOTIFY_URL_PREFIX):
        base_url = link.split("?")[0]
        parts = base_url.split("/")
        if len(parts) >= 5 and parts[3] in SUPPORTED_SPOTIFY_TYPES and parts[4]:
            return parts[4], parts[3]

    raise ValueError(f"Invalid Spotify link format: {link}")
