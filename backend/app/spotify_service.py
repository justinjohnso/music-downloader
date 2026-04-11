"""Spotify resolver service for backend link metadata lookups."""

import os

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from app.schemas import ResolveInfo, ResolvedTrack, SpotifyResolveResponse
from app.spotify_links import extract_spotify_info, is_spotify_link

SPOTIFY_CLIENT_ID_ENV = "SPOTIFY_CLIENT_ID"
SPOTIFY_CLIENT_SECRET_ENV = "SPOTIFY_CLIENT_SECRET"


class InvalidSpotifyLinkError(ValueError):
    """Raised when a Spotify link is malformed or unsupported."""


class SpotifyCredentialsError(RuntimeError):
    """Raised when required Spotify backend credentials are missing."""


class SpotifyLookupError(RuntimeError):
    """Raised when Spotify API lookup fails."""


def resolve_spotify_link(spotify_link: str) -> SpotifyResolveResponse:
    """Resolve a Spotify track/playlist link into normalized metadata.

    Args:
        spotify_link: Spotify URL/URI for a track or playlist.

    Returns:
        Response payload containing normalized tracks and playlist metadata.

    Raises:
        InvalidSpotifyLinkError: If the input link is invalid or unsupported.
        SpotifyCredentialsError: If required Spotify env credentials are missing.
        SpotifyLookupError: If Spotify API calls fail.
    """
    if not is_spotify_link(spotify_link):
        raise InvalidSpotifyLinkError(f"Invalid Spotify link format: {spotify_link}")

    spotify_id, spotify_type = extract_spotify_info(spotify_link)
    spotify_client = _build_spotify_client()

    try:
        if spotify_type == "track":
            track = spotify_client.track(spotify_id)
            resolved_track = _normalize_track(track)
            return SpotifyResolveResponse(
                tracks=[resolved_track],
                info=ResolveInfo(is_playlist=False, name=None),
            )

        if spotify_type == "playlist":
            playlist_info = spotify_client.playlist(spotify_id)
            playlist_name = playlist_info.get("name")
            tracks = _resolve_playlist_tracks(spotify_client, spotify_id)
            return SpotifyResolveResponse(
                tracks=tracks,
                info=ResolveInfo(is_playlist=True, name=playlist_name),
            )

        raise InvalidSpotifyLinkError(f"Unsupported Spotify link type: {spotify_type}")
    except spotipy.SpotifyException as exc:
        raise SpotifyLookupError("Spotify API request failed.") from exc


def _build_spotify_client() -> spotipy.Spotify:
    """Create a Spotipy client from backend environment credentials."""
    client_id = os.getenv(SPOTIFY_CLIENT_ID_ENV)
    client_secret = os.getenv(SPOTIFY_CLIENT_SECRET_ENV)

    if not client_id or not client_secret:
        raise SpotifyCredentialsError(
            "Spotify credentials are not configured in the backend environment."
        )

    return spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )
    )


def _resolve_playlist_tracks(
    spotify_client: spotipy.Spotify, spotify_playlist_id: str
) -> list[ResolvedTrack]:
    """Resolve and normalize all tracks in a Spotify playlist."""
    resolved_tracks: list[ResolvedTrack] = []
    results = spotify_client.playlist_items(
        spotify_playlist_id, additional_types=["track"]
    )

    while True:
        for item in results.get("items", []):
            track = item.get("track")
            if track:
                resolved_tracks.append(_normalize_track(track))

        if not results.get("next"):
            break

        results = spotify_client.next(results)

    return resolved_tracks


def _normalize_track(track_data: dict) -> ResolvedTrack:
    """Normalize Spotify track payload into the shared track contract."""
    artists = track_data.get("artists") or []
    artist_name = artists[0].get("name") if artists else "Unknown Artist"
    title = track_data.get("name") or "Unknown Title"
    return ResolvedTrack(artist=artist_name, title=title)
