import base64
from typing import List, Dict, Tuple, Any
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from pathlib import Path

# Pre-configured default Spotify credentials (base64 obfuscated)
_DEFAULT_CLIENT_ID = base64.b64decode(b"ZDczNzQ4YjdjZjU1NGJjNjg3NWQ2MmYyZmJhZmM5M2I=").decode()
_DEFAULT_CLIENT_SECRET = base64.b64decode(b"MTc0YjRhOWMxNTMzNDU1M2I3NjhjMDViZDQwMTBmNGE=").decode()

def _get_spotify_app_client(client_id: str, client_secret: str) -> spotipy.Spotify:
    """App-only Spotify client for simple public metadata lookups."""
    return spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )
    )


def _get_spotify_user_client(client_id: str, client_secret: str) -> spotipy.Spotify:
    """User-authenticated Spotify client for playlist access."""
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://127.0.0.1:8888/callback",
            scope="playlist-read-private playlist-read-collaborative",
            open_browser=True,
            cache_path=str(Path.home() / ".cache-music-downloader-spotify"),
        )
    )


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

    client_id = config_data.get("spotify", {}).get("client_id") or _DEFAULT_CLIENT_ID
    client_secret = config_data.get("spotify", {}).get("client_secret") or _DEFAULT_CLIENT_SECRET

    # Extract Spotify ID and type
    spotify_id, spotify_type = extract_spotify_info(spotify_link)

    tracks = []

    if spotify_type == "track":
        sp = _get_spotify_app_client(client_id, client_secret)

        track = sp.track(spotify_id)
        artist = track["artists"][0]["name"]
        title = track["name"]
        tracks.append({"artist": artist, "title": title})
        return tracks, {"is_playlist": False, "name": None}

    elif spotify_type == "playlist":
        sp = _get_spotify_user_client(client_id, client_secret)

        try:
            playlist_info = sp.playlist(spotify_id)
            playlist_name = playlist_info["name"]

            # Get playlist tracks
            results = sp.playlist_items(spotify_id, additional_types=["track"])

            for item in results["items"]:
                track = item.get("track") or item.get("item")
                if not track or track.get("type") != "track":
                    continue

                artist = (
                    track["artists"][0]["name"]
                    if track.get("artists")
                    else "Unknown Artist"
                )
                title = track.get("name", "Unknown Title")
                tracks.append({"artist": artist, "title": title})

            while results["next"]:
                results = sp.next(results)

                for item in results["items"]:
                    track = item.get("track") or item.get("item")
                    if not track or track.get("type") != "track":
                        continue

                    artist = (
                        track["artists"][0]["name"]
                        if track.get("artists")
                        else "Unknown Artist"
                    )
                    title = track.get("name", "Unknown Title")
                    tracks.append({"artist": artist, "title": title})

            return tracks, {"is_playlist": True, "name": playlist_name}

        except Exception as e:
            msg = str(e)
            if "401" in msg or "Valid user authentication required" in msg:
                raise RuntimeError(
                    "Spotify rejected this playlist request. "
                    "Make sure your Spotify app has redirect URI "
                    "'http://127.0.0.1:8888/callback' configured, "
                    "then sign in when prompted."
                ) from e
            raise

    else:
        raise ValueError(f"Unsupported Spotify link type: {spotify_type}")
