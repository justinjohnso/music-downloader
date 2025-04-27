"""
music-download.py

Script to search for and download music tracks from Deezer using Streamrip v2 API.

- Loads configuration from the user's TOML config file.
- Accepts a single search string (artist and track name) or a Spotify track/playlist URL.
- Searches Deezer for the track(s) and downloads them.

Requirements:
- streamrip v2 installed and configured
- Python 3.8+
- spotipy library (pip install spotipy)

Usage:
    python music-download.py "billie eilish when i was older"
    python music-download.py "https://open.spotify.com/track/4jvjzW7Hm0yK4LvvE0Paz9"
    python music-download.py "https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF"
    python music-download.py --verbose "billie eilish when i was older"

References:
- https://github.com/nathom/streamrip
"""

import sys
import os
import re
import asyncio
import argparse
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from dotenv import load_dotenv  # Add dotenv import

# Import existing libraries
from streamrip.client import DeezerClient
from streamrip.config import Config
from streamrip.db import Database, Dummy
from streamrip.media import PendingTrack
from streamrip.metadata import AlbumMetadata
from streamrip.media.artwork import download_artwork

# Import Spotify API library
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Find default config path across platforms
def get_default_config_path() -> str:
    """Get the default streamrip config path for the current platform."""
    if sys.platform == "darwin":  # macOS
        return str(Path.home() / "Library/Application Support/streamrip/config.toml")
    elif sys.platform == "win32":  # Windows
        return str(Path.home() / "AppData/Roaming/streamrip/config.toml")
    else:  # Linux and others
        return str(Path.home() / ".config/streamrip/config.toml")

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

def get_spotify_tracks(spotify_link: str) -> List[Dict[str, str]]:
    """
    Get track information from Spotify link.
    
    Args:
        spotify_link: Spotify track or playlist link
        
    Returns:
        List of dictionaries with track information (artist and title)
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Set up Spotify client
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError(
            "Spotify API credentials not found. Either:\n"
            "1. Create a .env file with SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET, or\n"
            "2. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables."
        )
    
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
    
    # Extract Spotify ID and type
    spotify_id, spotify_type = extract_spotify_info(spotify_link)
    
    tracks = []
    
    if spotify_type == "track":
        # Get single track
        track = sp.track(spotify_id)
        artist = track['artists'][0]['name']
        title = track['name']
        tracks.append({"artist": artist, "title": title})
    
    elif spotify_type == "playlist":
        # Get playlist tracks
        results = sp.playlist_items(spotify_id, additional_types=['track'])
        
        for item in results['items']:
            if 'track' in item and item['track']:
                track = item['track']
                artist = track['artists'][0]['name'] if track['artists'] else "Unknown Artist"
                title = track['name']
                tracks.append({"artist": artist, "title": title})
        
        # Handle playlists with more than 100 tracks (Spotify's pagination)
        while results['next']:
            results = sp.next(results)
            for item in results['items']:
                if 'track' in item and item['track']:
                    track = item['track']
                    artist = track['artists'][0]['name'] if track['artists'] else "Unknown Artist"
                    title = track['name']
                    tracks.append({"artist": artist, "title": title})
    
    else:
        raise ValueError(f"Unsupported Spotify link type: {spotify_type}")
    
    return tracks

async def download_track_with_client(client, config, search_string: str, db=None, verbose: bool = False) -> bool:
    """
    Search for a track on Deezer using the provided client and download the first result.

    Args:
        client: An initialized DeezerClient
        config: The loaded config
        search_string (str): The search query (artist and track name)
        db: The database instance to use
        verbose (bool): Whether to print detailed output

    Returns:
        bool: True if download was successful, False otherwise
    """
    try:
        # Search for the track
        try:
            results = await client.search(query=search_string, media_type="track")
        except Exception as e:
            print(f"Error during search: {e}")
            return False

        # Process search results
        tracks = results
        if isinstance(tracks, dict) and "data" in tracks:
            tracks = tracks["data"]
        if not tracks:
            print(f"No tracks found for query: '{search_string}'")
            return False

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
            return False

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
            return False
            
        try:
            # Resolve and download the track
            print(f"Downloading '{title}' by {artist}...")
            resolved = await pending.resolve()
            await resolved.rip()
            print(f"Successfully downloaded '{title}' by {artist}")
            return True
        except Exception as e:
            print(f"Error downloading track: {e}")
            return False
    except Exception as e:
        print(f"Error during track processing: {e}")
        return False

async def download_multiple_tracks(tracks: List[Dict[str, str]], config_path: str = None, verbose: bool = False) -> None:
    """
    Download multiple tracks from Deezer based on artist and title information.
    
    Args:
        tracks: List of dictionaries with track information (artist and title)
        config_path: Path to streamrip config file
        verbose: Whether to print detailed output
    """
    # Use provided config path or fall back to default
    config_path = config_path or get_default_config_path()
    
    if verbose:
        print(f"Using config file: {config_path}")
    
    # Load configuration and initialize client (only once for all tracks)
    config = Config(config_path)
    client = DeezerClient(config)
    db = Database(downloads=Dummy(), failed=Dummy())
    
    try:
        await client.login()
        if not getattr(client, "logged_in", False):
            print("Login failed. Check your Deezer credentials in the config file.")
            return
        print("Logged in to Deezer.")
        
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
    try:
        # Get tracks from Spotify
        print(f"Retrieving track information from Spotify...")
        
        # Run the synchronous Spotify API call in a thread
        tracks = await asyncio.get_event_loop().run_in_executor(None, get_spotify_tracks, spotify_link)
        
        if not tracks:
            print("No tracks found in the Spotify link.")
            return
            
        print(f"Found {len(tracks)} tracks")
        
        # Download tracks
        await download_multiple_tracks(tracks, config_path, verbose)
        
    except Exception as e:
        print(f"Error processing Spotify link: {e}")

def main() -> None:
    """Parse command line arguments and start the download process."""
    parser = argparse.ArgumentParser(description="Download music tracks from Deezer using Streamrip.")
    parser.add_argument("input", type=str, help="Search query (artist and track name) or Spotify link")
    parser.add_argument("-c", "--config", type=str, help="Path to streamrip config file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print detailed output")
    
    args = parser.parse_args()
    
    if is_spotify_link(args.input):
        # Handle Spotify link
        asyncio.run(process_spotify_link(args.input, args.config, args.verbose))
    else:
        # Handle regular search string
        asyncio.run(download_track(args.input, args.config, args.verbose))

if __name__ == "__main__":
    main()
