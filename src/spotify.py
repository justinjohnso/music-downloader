import json
from typing import List, Dict, Tuple, Any
from urllib import error, request

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


def is_spotify_link(link: str) -> bool:
    """Check if the provided string is a Spotify link."""
    return link.startswith("https://open.spotify.com/") or link.startswith("spotify:")


def extract_spotify_info(link: str) -> Tuple[str, str]:
    """Extract Spotify ID and type from a link."""
    # Handle URI format (spotify:track:1234567890)
    if link.startswith("spotify:"):
        parts = link.split(":")
        if len(parts) >= 3:
            return parts[2], parts[1]  # ID, type

    # Handle URL format (https://open.spotify.com/track/1234567890)
    elif link.startswith("https://open.spotify.com/"):
        # Remove query parameters if present
        base_url = link.split("?")[0]
        parts = base_url.split("/")
        if len(parts) >= 5:
            return parts[4], parts[3]  # ID, type

    raise ValueError(f"Invalid Spotify link format: {link}")


def get_spotify_tracks(
    spotify_link: str,
) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """
    Get track information from Spotify link.

    Args:
        spotify_link: Spotify track or playlist link

    Returns:
        Tuple of (tracks list, info dict with 'is_playlist' and 'name')
    """
    from src.config import (
        get_backend_config,
        load_config,
    )  # Import here to avoid circular import

    # Load configuration from mdl-config.toml file
    config_data = load_config()

    backend_resolve_url, backend_api_key = get_backend_config(config_data)

    spotify_config = config_data.get("spotify", {})
    if not isinstance(spotify_config, dict):
        spotify_config = {}

    client_id = spotify_config.get("client_id")
    client_secret = spotify_config.get("client_secret")

    if not isinstance(client_id, str):
        client_id = None
    else:
        client_id = client_id.strip() or None

    if not isinstance(client_secret, str):
        client_secret = None
    else:
        client_secret = client_secret.strip() or None

    has_local_credentials = bool(client_id and client_secret)

    backend_error: Exception | None = None
    if backend_resolve_url and backend_api_key:
        try:
            payload = json.dumps({"spotify_link": spotify_link}).encode("utf-8")
            backend_request = request.Request(
                backend_resolve_url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-API-Key": backend_api_key,
                },
                method="POST",
            )
            with request.urlopen(backend_request, timeout=15) as response:
                backend_response = json.loads(response.read().decode("utf-8"))

            tracks = backend_response.get("tracks")
            info = backend_response.get("info")
            if isinstance(tracks, list) and isinstance(info, dict):
                return tracks, info
            raise ValueError("Backend returned an invalid Spotify resolve payload.")
        except error.HTTPError as exc:
            detail = str(exc.reason)
            try:
                body = exc.read().decode("utf-8")
                error_payload = json.loads(body)
                detail = error_payload.get("detail") or detail
            except Exception:
                pass
            backend_error = RuntimeError(
                f"Spotify backend request failed with HTTP {exc.code}: {detail}"
            )
        except (error.URLError, json.JSONDecodeError, ValueError, TimeoutError) as exc:
            backend_error = RuntimeError(f"Spotify backend request failed: {exc}")
        except Exception as exc:
            backend_error = RuntimeError(f"Spotify backend request failed: {exc}")

    if has_local_credentials:
        sp = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret,
            )
        )

        # Extract Spotify ID and type
        spotify_id, spotify_type = extract_spotify_info(spotify_link)

        tracks = []

        if spotify_type == "track":
            # Get single track
            track = sp.track(spotify_id)
            artist = track["artists"][0]["name"]
            title = track["name"]
            tracks.append({"artist": artist, "title": title})
            return tracks, {"is_playlist": False, "name": None}

        elif spotify_type == "playlist":
            # Get playlist name
            playlist_info = sp.playlist(spotify_id)
            playlist_name = playlist_info["name"]

            # Get playlist tracks
            results = sp.playlist_items(spotify_id, additional_types=["track"])

            for item in results["items"]:
                if "track" in item and item["track"]:
                    track = item["track"]
                    artist = (
                        track["artists"][0]["name"]
                        if track["artists"]
                        else "Unknown Artist"
                    )
                    title = track["name"]
                    tracks.append({"artist": artist, "title": title})

            # Handle playlists with more than 100 tracks (Spotify's pagination)
            while results["next"]:
                results = sp.next(results)
                for item in results["items"]:
                    if "track" in item and item["track"]:
                        track = item["track"]
                        artist = (
                            track["artists"][0]["name"]
                            if track["artists"]
                            else "Unknown Artist"
                        )
                        title = track["name"]
                        tracks.append({"artist": artist, "title": title})

            return tracks, {"is_playlist": True, "name": playlist_name}

        else:
            raise ValueError(f"Unsupported Spotify link type: {spotify_type}")

    if backend_error is not None:
        raise backend_error

    raise ValueError(
        "Spotify is not configured. Set [backend] resolve_url/api_key or provide "
        "[spotify] client_id/client_secret."
    )
