import os
import asyncio
from typing import Optional, List, Dict
from streamrip.client import DeezerClient
from streamrip.config import Config
from streamrip.db import Database, Dummy
from streamrip.media import PendingTrack
from streamrip.metadata import AlbumMetadata
from streamrip.media.artwork import download_artwork


async def download_track_with_client(client, config, search_string: str, db=None, verbose: bool = False) -> Optional[str]:
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
                for_playlist=False
            )

            if verbose:
                print(f"Downloaded album artwork")

            # Create a PendingTrack with all required parameters
            pending = PendingTrack(
                id=track_id,
                album=album,
                client=client,
                config=config,
                folder=download_folder,
                db=db,
                cover_path=cover_path
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
            # Return the expected file path (though we don't have it exactly)
            return f"{title} by {artist}"  # Placeholder, as exact path is hard to determine
        except Exception as e:
            print(f"Error downloading track: {e}")
            return None
    except Exception as e:
        print(f"Error during track processing: {e}")
        return None


async def download_multiple_tracks(tracks: List[Dict[str, str]], config_path: str = None, verbose: bool = False, is_playlist: bool = False, playlist_name: Optional[str] = None) -> None:
    """
    Download multiple tracks from Deezer based on artist and title information.

    Args:
        tracks: List of dictionaries with track information (artist and title)
        config_path: Path to streamrip config file
        verbose: Whether to print detailed output
        is_playlist: Whether this is from a Spotify playlist
        playlist_name: Name of the playlist if applicable
    """
    from .config import load_config, ensure_streamrip_config_exists, apply_config_overrides

    # Load configuration from mdl-config.toml
    config_data = load_config()

    # Use provided config path or ensure default exists
    config_path = config_path or ensure_streamrip_config_exists()

    if verbose:
        print(f"Using config file: {config_path}")

    # Load configuration and initialize client (only once for all tracks)
    config = Config(config_path)
    apply_config_overrides(config, config_data)
    config.session.update_toml()  # Sync session changes back to file config
    client = DeezerClient(config)
    db = Database(downloads=Dummy(), failed=Dummy())

    try:
        await client.login()
        if not getattr(client, "logged_in", False):
            print("Login failed. Check your Deezer credentials in the config file.")
            return
        print("Logged in to Deezer.")

        # Debug: check what download folder is actually being used
        print(f"Actual download folder from config.file: {config.file.downloads.folder}")
        print(f"Session download folder: {config.session.downloads.folder}")

        successful_downloads = 0
        failed_downloads = 0

        total_tracks = len(tracks)
        print(f"Processing {total_tracks} tracks...")

        # Process each track
        for i, track in enumerate(tracks):
            artist = track.get("artist", "")
            title = track.get("title", "")
            search_string = f"{artist} {title}"

            print(f"\nProcessing track {i+1}/{total_tracks}: {artist} - {title}")

            # Use the download function with shared client
            result = await download_track_with_client(client, config, search_string, db, verbose)

            if result:
                successful_downloads += 1
            else:
                failed_downloads += 1

            # Add a small delay between downloads to avoid hammering the API
            if i < total_tracks - 1:
                await asyncio.sleep(1)

        print(f"\nDownload summary: {successful_downloads} successful, {failed_downloads} failed out of {total_tracks} total")

        # Generate M3U playlist file for Spotify playlists
        if is_playlist and successful_downloads > 0 and playlist_name:
            download_folder = config.file.downloads.folder
            # Sanitize playlist name for filename
            safe_name = "".join(c for c in playlist_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            m3u_filename = f"{safe_name}.m3u"
            m3u_path = os.path.join(download_folder, m3u_filename)
            try:
                # List all .mp3 files in the download folder
                mp3_files = [f for f in os.listdir(download_folder) if f.endswith('.mp3')]
                mp3_files.sort()  # Sort for consistent order
                with open(m3u_path, 'w', encoding='utf-8') as f:
                    for mp3 in mp3_files:
                        f.write(f"{mp3}\n")
                print(f"Generated M3U playlist '{playlist_name}' at: {m3u_path}")
            except Exception as e:
                print(f"Warning: Could not generate M3U playlist: {e}")

    finally:
        # Clean up client session
        if hasattr(client, "session") and client.session:
            try:
                if not client.session.closed:
                    # Cancel any pending requests
                    for task in asyncio.all_tasks():
                        if not task.done() and task != asyncio.current_task():
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass

                    # Close the session
                    await client.session.close()

                # Close the connector
                if hasattr(client.session, "_connector") and client.session._connector:
                    await client.session._connector.close()

                await asyncio.sleep(0.1)

                if verbose:
                    print("Successfully closed client session")
            except Exception as e:
                if verbose:
                    print(f"Error while closing client session: {e}")


async def download_track(search_string: str, config_path: str = None, verbose: bool = False) -> None:
    """
    Search for a track on Deezer using the provided search string and download the first result.

    Args:
        search_string (str): The search query (artist and track name).
        config_path (str, optional): Path to streamrip config file.
        verbose (bool): Whether to print detailed output.
    """
    from .config import load_config, ensure_streamrip_config_exists, apply_config_overrides

    # Load configuration from mdl-config.toml
    config_data = load_config()

    # Use provided config path or ensure default exists
    config_path = config_path or ensure_streamrip_config_exists()

    if verbose:
        print(f"Using config file: {config_path}")

    # Load configuration and initialize client
    config = Config(config_path)
    apply_config_overrides(config, config_data)
    config.session.update_toml()  # Sync session changes back to file config
    client = DeezerClient(config)

    try:
        await client.login()
        if not getattr(client, "logged_in", False):
            print("Login failed. Check your Deezer credentials in the config file.")
            return
        print("Logged in to Deezer.")

        # Debug: check what download folder is actually being used
        print(f"Actual download folder from config.file: {config.file.downloads.folder}")
        print(f"Session download folder: {config.session.downloads.folder}")

        # Use the shared download function
        await download_track_with_client(client, config, search_string, verbose=verbose)

    finally:
        # Clean up client session
        if hasattr(client, "session") and client.session:
            try:
                if not client.session.closed:
                    # Cancel any pending requests
                    for task in asyncio.all_tasks():
                        if not task.done() and task != asyncio.current_task():
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass

                    # Close the session
                    await client.session.close()

                # Close the connector
                if hasattr(client.session, "_connector") and client.session._connector:
                    await client.session._connector.close()

                await asyncio.sleep(0.1)

                if verbose:
                    print("Successfully closed client session")
            except Exception as e:
                if verbose:
                    print(f"Error while closing client session: {e}")


async def process_spotify_link(spotify_link: str, config_path: str = None, verbose: bool = False) -> None:
    """
    Process a Spotify link to download tracks.

    Args:
        spotify_link: Spotify track or playlist link
        config_path: Path to streamrip config file
        verbose: Whether to print detailed output
    """
    from .spotify import get_spotify_tracks

    try:
        # Get tracks from Spotify
        print(f"Retrieving track information from Spotify...")

        # Run the synchronous Spotify API call in a thread
        tracks, info = await asyncio.get_event_loop().run_in_executor(None, get_spotify_tracks, spotify_link)

        if not tracks:
            print("No tracks found in the Spotify link.")
            return

        print(f"Found {len(tracks)} tracks")

        # Download tracks
        playlist_name = info['name'] if info['is_playlist'] else None
        await download_multiple_tracks(tracks, config_path, verbose, info['is_playlist'], playlist_name)

    except Exception as e:
        print(f"Error processing Spotify link: {e}")
