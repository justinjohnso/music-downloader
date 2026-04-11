"""Request and response contracts for the Spotify backend API."""

from typing import Literal

from pydantic import BaseModel, Field


class SpotifyResolveRequest(BaseModel):
    """Request payload for resolving a Spotify link."""

    spotify_link: str = Field(min_length=1)


class ResolvedTrack(BaseModel):
    """Normalized track payload returned by Spotify resolution."""

    artist: str
    title: str


class ResolveInfo(BaseModel):
    """Metadata describing the resolved Spotify payload."""

    is_playlist: bool
    name: str | None = None


class SpotifyResolveResponse(BaseModel):
    """Response payload for a resolved Spotify link."""

    tracks: list[ResolvedTrack]
    info: ResolveInfo


class ErrorResponse(BaseModel):
    """Standard API error payload."""

    detail: str
    code: Literal["invalid_spotify_link", "spotify_error", "internal_error"] | None = (
        None
    )
