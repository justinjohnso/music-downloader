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
    from src.config import load_config  # Import here to avoid circular import

    # Load configuration from mdl-config.toml file
    config_data = load_config()

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

    if client_id and client_secret:
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

    raise ValueError(
        "Spotify credentials not found in mdl-config.toml. "
        "Please provide [spotify] client_id and client_secret."
    )
