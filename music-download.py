"""
music-download.py

Script to search for and download a track from Deezer using Streamrip v2 API.

- Loads configuration from the user's TOML config file.
- Accepts a single search string (artist and track name, e.g., 'billie eilish when i was older').
- Searches Deezer for the track and downloads the first result.

Requirements:
- streamrip v2 installed and configured
- Python 3.8+

Usage:
    python music-download.py "billie eilish when i was older"
    python music-download.py --verbose "billie eilish when i was older"

References:
- https://github.com/nathom/streamrip
"""

import sys
import os
import asyncio
import argparse
from typing import Optional
from pathlib import Path

from streamrip.client import DeezerClient
from streamrip.config import Config
from streamrip.db import Database, Dummy
from streamrip.media import PendingTrack
from streamrip.metadata import AlbumMetadata
from streamrip.media.artwork import download_artwork

# Find default config path across platforms
def get_default_config_path() -> str:
    """Get the default streamrip config path for the current platform."""
    if sys.platform == "darwin":  # macOS
        return str(Path.home() / "Library/Application Support/streamrip/config.toml")
    elif sys.platform == "win32":  # Windows
        return str(Path.home() / "AppData/Roaming/streamrip/config.toml")
    else:  # Linux and others
        return str(Path.home() / ".config/streamrip/config.toml")

async def download_track(search_string: str, config_path: str = None, verbose: bool = False) -> None:
    """
    Search for a track on Deezer using the provided search string and download the first result.

    Args:
        search_string (str): The search query (artist and track name).
        config_path (str, optional): Path to streamrip config file.
        verbose (bool): Whether to print detailed output.
    """
    # Use provided config path or fall back to default
    config_path = config_path or get_default_config_path()
    
    if verbose:
        print(f"Using config file: {config_path}")
    
    # Load configuration and initialize client
    config = Config(config_path)
    client = DeezerClient(config)
    
    try:
        await client.login()
        if not getattr(client, "logged_in", False):
            print("Login failed. Check your Deezer credentials in the config file.")
            return
        print("Logged in to Deezer.")

        # Search for the track
        try:
            results = await client.search(query=search_string, media_type="track")
        except Exception as e:
            print(f"Error during search: {e}")
            return

        # Process search results
        tracks = results
        if isinstance(tracks, dict) and "data" in tracks:
            tracks = tracks["data"]
        if not tracks:
            print(f"No tracks found for query: '{search_string}'")
            return

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
            return

        # Create database and prepare for download
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
            return
            
        try:
            # Resolve and download the track
            print(f"Downloading '{title}' by {artist}...")
            resolved = await pending.resolve()
            await resolved.rip()
            print(f"Successfully downloaded '{title}' by {artist}")
        except Exception as e:
            print(f"Error downloading track: {e}")
    
    finally:
        # More thorough cleanup of client session
        if hasattr(client, "session") and client.session:
            try:
                # Close any outstanding connections first
                if not client.session.closed:
                    # Cancel any pending requests
                    for task in asyncio.all_tasks():
                        if not task.done() and task != asyncio.current_task():
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass
                    
                    # Now close the session
                    await client.session.close()
                
                # Make sure the connector is also closed
                if hasattr(client.session, "_connector") and client.session._connector:
                    await client.session._connector.close()
                
                # Give the event loop a moment to process the closures
                await asyncio.sleep(0.1)
                
                if verbose:
                    print("Successfully closed client session")
            except Exception as e:
                if verbose:
                    print(f"Error while closing client session: {e}")


def main() -> None:
    """Parse command line arguments and start the download process."""
    parser = argparse.ArgumentParser(description="Download music tracks from Deezer using Streamrip.")
    parser.add_argument("search", type=str, help="Search query (artist and track name)")
    parser.add_argument("-c", "--config", type=str, help="Path to streamrip config file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print detailed output")
    
    args = parser.parse_args()
    
    asyncio.run(download_track(args.search, args.config, args.verbose))

if __name__ == "__main__":
    main()
