from __future__ import annotations

from typing import Any, Callable

TrackCandidate = dict[str, Any]
SelectionCallback = Callable[
    [str, list[TrackCandidate], dict[str, str] | None], int | None
]


def extract_track_results(results: Any) -> list[dict[str, Any]]:
    """Flatten Deezer result pages while retaining their source order."""
    if isinstance(results, dict):
        if "data" in results:
            return extract_track_results(results["data"])
        return [results]
    if isinstance(results, list):
        return [track for result in results for track in extract_track_results(result)]
    return []


def build_track_candidate(track: dict[str, Any]) -> TrackCandidate | None:
    """Normalize a result with identifiers required for a track download."""
    identifier = track.get("id")
    album = track.get("album")
    if not identifier or not isinstance(album, dict) or not album.get("id"):
        return None
    artist = track.get("artist") or track.get("artists")
    if isinstance(artist, list):
        artist = artist[0] if artist else None
    if isinstance(artist, dict):
        artist = artist.get("name")
    title = track.get("title") or track.get("name")
    if not isinstance(title, str) or not title.strip():
        return None
    return {
        "id": str(identifier),
        "album_id": str(album["id"]),
        "title": title,
        "artist": artist if isinstance(artist, str) else "Unknown Artist",
        "album": album.get("title") or "Unknown Album",
        "duration": track.get("duration"),
        "explicit": bool(track.get("explicit_lyrics")),
        "track": track,
    }


def format_track_candidate(candidate: TrackCandidate, index: int | None = None) -> str:
    """Format album and duration information for match selection."""
    prefix = f"{index + 1}. " if index is not None else ""
    duration = candidate.get("duration")
    timing = ""
    if isinstance(duration, int) and duration > 0:
        minutes, seconds = divmod(duration, 60)
        timing = f" [{minutes}:{seconds:02d}]"
    explicit = " [E]" if candidate.get("explicit") else ""
    return f"{prefix}{candidate['artist']} - {candidate['title']} ({candidate['album']}){timing}{explicit}"


async def search_track_candidates_with_client(
    client: Any, query: str, result_limit: int = 10
) -> list[TrackCandidate]:
    """Return selectable Deezer matches without downloading any audio."""
    if result_limit < 1:
        raise ValueError("Result limit must be positive")
    results = extract_track_results(
        await client.search(query=query, media_type="track")
    )
    if not results and " - " in query:
        results = extract_track_results(
            await client.search(query=query.replace(" - ", " "), media_type="track")
        )
    candidates = [
        candidate
        for result in results
        if (candidate := build_track_candidate(result)) is not None
    ]
    return candidates[:result_limit]


async def search_track_candidates(
    query: str,
    config_path: str | None = None,
    verbose: bool = False,
    result_limit: int = 10,
) -> list[TrackCandidate]:
    """Search with current mdl configuration and close only the owned session."""
    from .config import (
        Config,
        load_config,
        ensure_streamrip_config_exists,
        apply_config_overrides,
    )
    from streamrip.client import DeezerClient
    from streamrip.exceptions import AuthenticationError, MissingCredentialsError

    config = Config(config_path or ensure_streamrip_config_exists())
    apply_config_overrides(config, load_config())
    client = DeezerClient(config)
    try:
        try:
            await client.login()
        except (AuthenticationError, MissingCredentialsError) as error:
            raise RuntimeError(
                "Deezer login failed. Run mdl --set-arl or mdl --setup."
            ) from error
        return await search_track_candidates_with_client(client, query, result_limit)
    finally:
        session = getattr(client, "session", None)
        if session is not None and not session.closed:
            await session.close()
