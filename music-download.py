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

References:
- https://github.com/nathom/streamrip
"""

import sys
import asyncio
from typing import Optional
from streamrip.client import DeezerClient
from streamrip.config import Config
from streamrip.db import Downloads, Failed, Database
from streamrip.media import PendingTrack

CONFIG_PATH = "/Users/justin/Library/Application Support/streamrip/config.toml"

async def download_track(search_string: str) -> None:
    """
    Search for a track on Deezer using the provided search string and download the first result.

    Args:
        search_string (str): The search query (artist and track name).
    """
    config = Config(CONFIG_PATH)
    client = DeezerClient(config)
    await client.login()
    if not getattr(client, "logged_in", False):
        print("Login failed. Check your Deezer credentials in the config file.")
        return
    print("Logged in to Deezer.")

    # Search for the track
    try:
        # Use keyword arguments to avoid argument order confusion
        results = await client.search(query=search_string, media_type="track")
    except Exception as e:
        print(f"Error during search: {e}")
        return

    # results is a list of tracks
    tracks = results

    # The API response is a dict with a 'data' key containing the list of tracks
    if isinstance(tracks, dict) and "data" in tracks:
        tracks = tracks["data"]
    if not tracks:
        print(f"No tracks found for query: '{search_string}'")
        return

    track = tracks[0]
    # If the first track is a dict with a 'data' key, extract the first item from 'data'
    if isinstance(track, dict) and "data" in track:
        track = track["data"][0]
    print(f"First track object: {track}")  # Debug: print the raw track object
    track_id = track.get("id")
    title = track.get("title")
    artist = None
    if isinstance(track.get("artist"), dict):
        artist = track["artist"].get("name")
    elif isinstance(track.get("artist"), str):
        artist = track["artist"]
    print(f"Found track: {title} by {artist} (id: {track_id})")

    if not track_id:
        print("Error: Track object does not contain an 'id' field. Full object printed above.")
        return

    # Debug: Print the config structure to see how to access database paths
    print("Config structure:")
    print("Config type:", type(config))
    print("Config dir:", dir(config))
    
    # Try different ways to access config data
    try:
        # Check if the config object has a __dict__ attribute we can inspect
        if hasattr(config, '__dict__'):
            print("Config __dict__:", config.__dict__)
        
        # Try accessing like a dictionary
        if hasattr(config, 'get'):
            print("Config db path:", config.get('db', None))
            print("Config downloads_db path:", config.get('downloads_db', None))
            
        # Try accessing toml_dict or data attribute which is common in TOML parsers
        if hasattr(config, 'toml_dict'):
            print("Config toml_dict:", config.toml_dict)
        if hasattr(config, 'data'):
            print("Config data:", config.data)
    except Exception as e:
        print(f"Error inspecting config: {e}")

    # Use the simple Database implementation with Dummy objects
    from streamrip.db import Dummy
    from streamrip.metadata import AlbumMetadata
    
    # Create a simple database object with Dummy handlers
    db = Database(downloads=Dummy(), failed=Dummy())
    
    print("Using simple Dummy database implementation")
    
    # Get the download folder from config
    download_folder = config.file.downloads.folder
    
    # First we need to get the album metadata for the track
    try:
        album_id = track["album"]["id"]
        album_data = await client.get_metadata(album_id, "album")
        # Use the proper method based on source code analysis
        album = AlbumMetadata.from_album_resp(album_data, client.source)
        print(f"Got album metadata for: {album.album}")
        
        # Create a PendingTrack with all required parameters including album
        pending = PendingTrack(
            id=track_id,
            album=album,
            client=client,
            config=config,
            folder=download_folder,
            db=db,
            cover_path=None
        )
    except Exception as e:
        print(f"Error getting album metadata: {e}")
        return
    try:
        resolved = await pending.resolve()
    except Exception as e:
        print(f"Error resolving track: {e}")
        return
    print("Track metadata:", resolved.meta)

    try:
        await resolved.rip()
        print("Download complete.")
    except Exception as e:
        print(f"Error downloading track: {e}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python music-download.py \"artist and track name\"")
        sys.exit(1)
    search_string = sys.argv[1]
    asyncio.run(download_track(search_string))

if __name__ == "__main__":
    main()
