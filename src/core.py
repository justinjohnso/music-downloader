import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any
from streamrip.client import DeezerClient
from streamrip.config import Config
from streamrip.db import Database, Dummy
from streamrip.exceptions import AuthenticationError, MissingCredentialsError
from streamrip.media import PendingTrack
from streamrip.metadata import AlbumMetadata
from streamrip.media.artwork import download_artwork

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".aac", ".wav"}


def _print_spotify_configuration_help() -> None:
    """Print guidance for configuring Spotify metadata resolution."""
    print(
        "Spotify metadata lookup requires one of the following in mdl-config.toml:\n"
        "  [backend] resolve_url + api_key (recommended)\n"
        "  [spotify] client_id + client_secret (local fallback)"
    )


def _normalize_spotify_payload(
    tracks: list[dict[str, Any]], info: dict[str, Any], verbose: bool
) -> tuple[list[dict[str, str]], bool, str | None]:
    """Normalize Spotify payload returned from backend/local resolver."""
    normalized_tracks: list[dict[str, str]] = []
    for index, track in enumerate(tracks):
        if not isinstance(track, dict):
            if verbose:
                print(f"Skipping Spotify track {index + 1}: expected object payload.")
            continue

        artist = track.get("artist")
        title = track.get("title")
        if not isinstance(artist, str) or not isinstance(title, str):
            if verbose:
                print(
                    f"Skipping Spotify track {index + 1}: missing string artist/title."
                )
            continue

        artist = artist.strip()
        title = title.strip()
        if not artist or not title:
            if verbose:
                print(f"Skipping Spotify track {index + 1}: empty artist/title values.")
            continue

        normalized_tracks.append({"artist": artist, "title": title})

    is_playlist = bool(info.get("is_playlist")) if isinstance(info, dict) else False
    playlist_name = info.get("name") if isinstance(info, dict) else None
    if not isinstance(playlist_name, str):
        playlist_name = None

    return normalized_tracks, is_playlist, playlist_name


@asynccontextmanager
async def managed_client(client, verbose: bool = False):
    """Async context manager that ensures proper cleanup of DeezerClient sessions."""
    try:
        yield client
    finally:
        if hasattr(client, "session") and client.session:
            try:
                if not client.session.closed:
                    for task in asyncio.all_tasks():
                        if not task.done() and task != asyncio.current_task():
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass
                    await client.session.close()
                if hasattr(client.session, "_connector") and client.session._connector:
                    await client.session._connector.close()
                await asyncio.sleep(0.1)
                if verbose:
                    print("Successfully closed client session")
            except Exception as e:
                if verbose:
                    print(f"Error while closing client session: {e}")


async def download_track_with_client(
    client, config, search_string: str, db=None, verbose: bool = False
) -> Optional[str]:
    """
    Search for a track on Deezer using the provided client and download the first result.

    Args:
        client: An initialized DeezerClient
        config: The loaded config
        search_string (str): The search query (artist and track name).
        db: The database instance to use
        verbose (bool): Whether to print detailed output

    Returns:
        The file path if successful, None otherwise
    """
    try:
        # Search for the track
        try:
            results = await client.search(query=search_string, media_type="track")
        except Exception as e:
            print(f"Error during search: {e}")
            return None

        # Process search results
        tracks = results
        if isinstance(tracks, dict) and "data" in tracks:
            tracks = tracks["data"]
        if not tracks:
            print(f"No tracks found for query: '{search_string}'")
            return None

        track = tracks[0]
        if isinstance(track, dict) and "data" in track:
            track = track["data"][0]

        # Extract track information
        track_id = track.get("id")
        title = track.get("title")
        artist = None
        if isinstance(track.get("artist"), dict):
            artist = track["artist"].get("name")
        elif isinstance(track.get("artist"), str):
            artist = track["artist"]
        print(f"Found track: {title} by {artist}")

        if not track_id:
            print("Error: Could not determine track ID.")
            return None

        # Use provided database or create a new one
        if db is None:
            db = Database(downloads=Dummy(), failed=Dummy())
        download_folder = config.file.downloads.folder

        try:
            # Get album metadata
            album_id = track["album"]["id"]
            album_data = await client.get_metadata(album_id, "album")
            album = AlbumMetadata.from_album_resp(album_data, client.source)

            if verbose:
                print(f"Got album metadata: {album.album}")

            # Download album artwork
            artwork_folder = os.path.join(download_folder, ".artwork")
            os.makedirs(artwork_folder, exist_ok=True)

            cover_path, _ = await download_artwork(
                client.session,
                artwork_folder,
                album.covers,
                config.file.artwork,
                for_playlist=False,
            )

            if verbose:
                print("Downloaded album artwork")

            # Create a PendingTrack with all required parameters
            pending = PendingTrack(
                id=track_id,
                album=album,
                client=client,
                config=config,
                folder=download_folder,
                db=db,
                cover_path=cover_path,
            )
        except Exception as e:
            print(f"Error preparing download: {e}")
            return None

        try:
            # Resolve and download the track
            print(f"Downloading '{title}' by {artist}...")
            resolved = await pending.resolve()
            await resolved.rip()
            print(f"Successfully downloaded '{title}' by {artist}")
            # Find the actual downloaded file by scanning for the most recently
            # modified file whose name contains the title (case-insensitive)
            title_lower = title.lower() if title else ""
            best_match = None
            best_mtime = 0.0
            for entry in os.scandir(download_folder):
                if not entry.is_file():
                    continue
                p = Path(entry.name)
                if p.suffix.lower() not in AUDIO_EXTENSIONS:
                    continue
                if title_lower and title_lower in entry.name.lower():
                    mtime = entry.stat().st_mtime
                    if mtime > best_mtime:
                        best_mtime = mtime
                        best_match = entry.path
            return best_match if best_match else f"{title} by {artist}"
        except Exception as e:
            print(f"Error downloading track: {e}")
            return None
    except Exception as e:
        print(f"Error during track processing: {e}")
        return None


async def download_multiple_tracks(
    tracks: List[Dict[str, str]],
    config_path: str = None,
    verbose: bool = False,
    is_playlist: bool = False,
    playlist_name: Optional[str] = None,
) -> None:
    """
    Download multiple tracks from Deezer based on artist and title information.

    Args:
        tracks: List of dictionaries with track information (artist and title)
        config_path: Path to streamrip config file
        verbose: Whether to print detailed output
        is_playlist: Whether this is from a Spotify playlist
        playlist_name: Name of the playlist if applicable
    """
    from src.config import (
        load_config,
        ensure_streamrip_config_exists,
        merge_mdl_config_into_streamrip,
    )

    # Load configuration from mdl-config.toml
    config_data = load_config()

    # Use provided config path or ensure default exists
    config_path = config_path or ensure_streamrip_config_exists()

    # Merge mdl settings into streamrip's config on disk before loading
    merge_mdl_config_into_streamrip(config_path, config_data)

    if verbose:
        print(f"Using config file: {config_path}")

    # Load configuration and initialize client (only once for all tracks)
    config = Config(config_path)
    client = DeezerClient(config)
    db = Database(downloads=Dummy(), failed=Dummy())

    async with managed_client(client, verbose):
        if verbose:
            arl = config.session.deezer.arl
            print(
                f"Deezer ARL: {arl[:8]}...{arl[-4:]}" if arl else "Deezer ARL: NOT SET"
            )
        try:
            await client.login()
        except MissingCredentialsError:
            print("No Deezer ARL configured. Run 'mdl --setup' to set one up.")
            return
        except AuthenticationError:
            print(
                "Deezer ARL is invalid or expired (they last ~3-4 months). Get a new one:\nhttps://github.com/nathom/streamrip/wiki/Finding-Your-Deezer-ARL-Cookie\nThen run 'mdl --setup' to update it."
            )
            return
        if not getattr(client, "logged_in", False):
            print("Deezer login failed. Check your ARL or run 'mdl --setup'.")
            return
        print("Logged in to Deezer.")

        if verbose:
            print(f"Download folder: {config.session.downloads.folder}")

        successful_downloads = 0
        failed_downloads = 0
        downloaded_files: List[str] = []

        total_tracks = len(tracks)
        print(f"Processing {total_tracks} tracks...")

        # Process each track
        for i, track in enumerate(tracks):
            artist = track.get("artist", "")
            title = track.get("title", "")
            search_string = f"{artist} {title}"

            print(f"\nProcessing track {i+1}/{total_tracks}: {artist} - {title}")

            # Use the download function with shared client
            result = await download_track_with_client(
                client, config, search_string, db, verbose
            )

            if result:
                successful_downloads += 1
                downloaded_files.append(result)
            else:
                failed_downloads += 1

            # Add a small delay between downloads to avoid hammering the API
            if i < total_tracks - 1:
                await asyncio.sleep(1)

        print(
            f"\nDownload summary: {successful_downloads} successful, {failed_downloads} failed out of {total_tracks} total"
        )

        # Generate M3U playlist file for Spotify playlists
        if is_playlist and downloaded_files and playlist_name:
            download_folder = config.file.downloads.folder
            # Sanitize playlist name for filename
            safe_name = "".join(
                c for c in playlist_name if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            m3u_filename = f"{safe_name}.m3u"
            m3u_path = os.path.join(download_folder, m3u_filename)
            try:
                # Only include files from this session that are actual paths on disk
                session_files = sorted(
                    Path(f).name for f in downloaded_files if os.path.isfile(f)
                )
                with open(m3u_path, "w", encoding="utf-8") as f:
                    for filename in session_files:
                        f.write(f"{filename}\n")
                print(f"Generated M3U playlist '{playlist_name}' at: {m3u_path}")
            except Exception as e:
                print(f"Warning: Could not generate M3U playlist: {e}")


async def download_track(
    search_string: str, config_path: str = None, verbose: bool = False
) -> None:
    """
    Search for a track on Deezer using the provided search string and download the first result.

    Args:
        search_string (str): The search query (artist and track name).
        config_path (str, optional): Path to streamrip config file.
        verbose (bool): Whether to print detailed output.
    """
    from src.config import (
        load_config,
        ensure_streamrip_config_exists,
        merge_mdl_config_into_streamrip,
    )

    # Load configuration from mdl-config.toml
    config_data = load_config()

    # Use provided config path or ensure default exists
    config_path = config_path or ensure_streamrip_config_exists()

    # Merge mdl settings into streamrip's config on disk before loading
    merge_mdl_config_into_streamrip(config_path, config_data)

    if verbose:
        print(f"Using config file: {config_path}")

    # Load configuration and initialize client
    config = Config(config_path)
    client = DeezerClient(config)

    async with managed_client(client, verbose):
        try:
            await client.login()
        except MissingCredentialsError:
            print("No Deezer ARL configured. Run 'mdl --setup' to set one up.")
            return
        except AuthenticationError:
            print(
                "Deezer ARL is invalid or expired (they last ~3-4 months). Get a new one:\nhttps://github.com/nathom/streamrip/wiki/Finding-Your-Deezer-ARL-Cookie\nThen run 'mdl --setup' to update it."
            )
            return
        if not getattr(client, "logged_in", False):
            print("Deezer login failed. Check your ARL or run 'mdl --setup'.")
            return
        print("Logged in to Deezer.")

        if verbose:
            print(f"Download folder: {config.session.downloads.folder}")

        # Use the shared download function
        await download_track_with_client(client, config, search_string, verbose=verbose)


async def process_spotify_link(
    spotify_link: str, config_path: str = None, verbose: bool = False
) -> None:
    """
    Process a Spotify link to download tracks.

    Args:
        spotify_link: Spotify track or playlist link
        config_path: Path to streamrip config file
        verbose: Whether to print detailed output
    """
    from src.spotify import get_spotify_tracks

    try:
        # Get tracks from Spotify
        print("Retrieving track information from Spotify...")

        # Run the synchronous Spotify API call in a thread
        tracks, info = await asyncio.get_event_loop().run_in_executor(
            None, get_spotify_tracks, spotify_link
        )

        normalized_tracks, is_playlist, playlist_name = _normalize_spotify_payload(
            tracks, info, verbose
        )

        if not normalized_tracks:
            print("No tracks found in the Spotify link.")
            return

        print(f"Found {len(normalized_tracks)} tracks")

        # Download tracks
        await download_multiple_tracks(
            normalized_tracks, config_path, verbose, is_playlist, playlist_name
        )

    except (AuthenticationError, MissingCredentialsError):
        pass  # Already handled in download_multiple_tracks
    except Exception as e:
        print(f"Error processing Spotify link: {e}")
        if "Spotify backend request failed" in str(
            e
        ) or "Spotify is not configured" in str(e):
            _print_spotify_configuration_help()
        if verbose:
            import traceback

            traceback.print_exc()
