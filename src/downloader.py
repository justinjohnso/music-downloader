import sys
import os
import re
import asyncio
import argparse
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import tomlkit

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
def load_config() -> Dict:
    """Load configuration from mdl-config.toml file."""
    config_path = Path.cwd() / "mdl-config.toml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return tomlkit.parse(f.read())
    return {}


def ensure_streamrip_config_exists() -> str:
    """Ensure the streamrip config file exists and return its path."""
    config_path = get_default_config_path()

    # Check if config file exists
    if not Path(config_path).exists():
        print(f"Streamrip config not found at {config_path}, creating default config...")
        try:
            # Create the config directory if it doesn't exist
            Path(config_path).parent.mkdir(parents=True, exist_ok=True)

            # Use streamrip's command to create the default config
            import subprocess
            result = subprocess.run(['rip', 'config', 'open'],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and Path(config_path).exists():
                print(f"Created default streamrip config at {config_path}")
            else:
                raise Exception(f"rip config open failed: {result.stderr}")

        except Exception as e:
            print(f"Warning: Could not create default streamrip config: {e}")
            print("You may need to run 'rip config open' manually to create the config file.")
            # As a fallback, try to create an empty file
            try:
                Path(config_path).touch()
            except:
                pass

    return config_path


def get_default_config_path() -> str:
    """Get the default streamrip config path for the current platform."""
    if sys.platform == "darwin":  # macOS
        return str(Path.home() / "Library/Application Support/streamrip/config.toml")
    elif sys.platform == "win32":  # Windows
        return str(Path.home() / "AppData/Roaming/streamrip/config.toml")
    else:  # Linux and others
        return str(Path.home() / ".config/streamrip/config.toml")


def apply_config_overrides(config: Config, config_data: Dict) -> None:
    """
    Apply configuration overrides from config.toml to the streamrip config.

    This allows all streamrip configuration to be managed via config.toml file
    instead of being stored in the streamrip TOML config directly.

    Supported overrides include all streamrip configuration variables:
        - Credentials: deezer, qobuz, tidal, soundcloud, youtube sections
        - Downloads: downloads section
        - Artwork: artwork section
        - Metadata: metadata section
        - File paths: filepaths section
        - Conversions: conversions section
        - Database: database section
        - Filters: qobuz_filters section
        - CLI: cli section
        - LastFM: lastfm section
        - Misc: misc section

    Args:
        config: The loaded Config object to be modified
        config_data: The loaded configuration data from config.toml
    """

    # Debug: print what we're overriding
    if config_data:
        print(f"Applying config overrides from {len(config_data)} sections")

    # Apply configuration values from config_data to config.session
    # Session/Credentials - apply from config_data
    if "deezer" in config_data:
        deezer = config_data["deezer"]
        if deezer.get("arl") is not None:
            config.session.deezer.arl = deezer["arl"]
        if deezer.get("quality") is not None:
            config.session.deezer.quality = deezer["quality"]
        if deezer.get("use_deezloader") is not None:
            config.session.deezer.use_deezloader = deezer["use_deezloader"]
        if deezer.get("deezloader_warnings") is not None:
            config.session.deezer.deezloader_warnings = deezer["deezloader_warnings"]

    if "qobuz" in config_data:
        qobuz = config_data["qobuz"]
        if qobuz.get("email_or_userid") is not None:
            config.session.qobuz.email_or_userid = qobuz["email_or_userid"]
        if qobuz.get("password_or_token") is not None:
            config.session.qobuz.password_or_token = qobuz["password_or_token"]
        if qobuz.get("use_auth_token") is not None:
            config.session.qobuz.use_auth_token = qobuz["use_auth_token"]
        if qobuz.get("app_id") is not None:
            config.session.qobuz.app_id = qobuz["app_id"]
        if qobuz.get("quality") is not None:
            config.session.qobuz.quality = qobuz["quality"]
        if qobuz.get("download_booklets") is not None:
            config.session.qobuz.download_booklets = qobuz["download_booklets"]
        if qobuz.get("secrets") is not None:
            config.session.qobuz.secrets = qobuz["secrets"]

    if "tidal" in config_data:
        tidal = config_data["tidal"]
        if tidal.get("user_id") is not None:
            config.session.tidal.user_id = tidal["user_id"]
        if tidal.get("country_code") is not None:
            config.session.tidal.country_code = tidal["country_code"]
        if tidal.get("access_token") is not None:
            config.session.tidal.access_token = tidal["access_token"]
        if tidal.get("refresh_token") is not None:
            config.session.tidal.refresh_token = tidal["refresh_token"]
        if tidal.get("token_expiry") is not None:
            config.session.tidal.token_expiry = tidal["token_expiry"]
        if tidal.get("quality") is not None:
            config.session.tidal.quality = tidal["quality"]
        if tidal.get("download_videos") is not None:
            config.session.tidal.download_videos = tidal["download_videos"]

    if "soundcloud" in config_data:
        soundcloud = config_data["soundcloud"]
        if soundcloud.get("client_id") is not None:
            config.session.soundcloud.client_id = soundcloud["client_id"]
        if soundcloud.get("app_version") is not None:
            config.session.soundcloud.app_version = soundcloud["app_version"]
        if soundcloud.get("quality") is not None:
            config.session.soundcloud.quality = soundcloud["quality"]

    if "youtube" in config_data:
        youtube = config_data["youtube"]
        if youtube.get("video_downloads_folder") is not None:
            config.session.youtube.video_downloads_folder = youtube["video_downloads_folder"]
        if youtube.get("quality") is not None:
            config.session.youtube.quality = youtube["quality"]
        if youtube.get("download_videos") is not None:
            config.session.youtube.download_videos = youtube["download_videos"]

    # Top-level sections
    if "downloads" in config_data:
        downloads = config_data["downloads"]
        print(f"Setting downloads folder to: {downloads.get('folder')}")
        if downloads.get("folder") is not None:
            config.session.downloads.folder = os.path.expanduser(downloads["folder"])
            print(f"Downloads folder set to: {config.session.downloads.folder}")
        if downloads.get("source_subdirectories") is not None:
            config.session.downloads.source_subdirectories = downloads["source_subdirectories"]
        if downloads.get("disc_subdirectories") is not None:
            config.session.downloads.disc_subdirectories = downloads["disc_subdirectories"]
        if downloads.get("concurrency") is not None:
            config.session.downloads.concurrency = downloads["concurrency"]
        if downloads.get("max_connections") is not None:
            config.session.downloads.max_connections = downloads["max_connections"]
        if downloads.get("requests_per_minute") is not None:
            config.session.downloads.requests_per_minute = downloads["requests_per_minute"]
        if downloads.get("verify_ssl") is not None:
            config.session.downloads.verify_ssl = downloads["verify_ssl"]

    if "artwork" in config_data:
        artwork = config_data["artwork"]
        if artwork.get("embed") is not None:
            config.session.artwork.embed = artwork["embed"]
        if artwork.get("embed_size") is not None:
            config.session.artwork.embed_size = artwork["embed_size"]
        if artwork.get("embed_max_width") is not None:
            config.session.artwork.embed_max_width = artwork["embed_max_width"]
        if artwork.get("save_artwork") is not None:
            config.session.artwork.save_artwork = artwork["save_artwork"]
        if artwork.get("saved_max_width") is not None:
            config.session.artwork.saved_max_width = artwork["saved_max_width"]

    if "metadata" in config_data:
        metadata = config_data["metadata"]
        if metadata.get("set_playlist_to_album") is not None:
            config.session.metadata.set_playlist_to_album = metadata["set_playlist_to_album"]
        if metadata.get("renumber_playlist_tracks") is not None:
            config.session.metadata.renumber_playlist_tracks = metadata["renumber_playlist_tracks"]
        if metadata.get("exclude") is not None:
            config.session.metadata.exclude = metadata["exclude"]

    if "filepaths" in config_data:
        filepaths = config_data["filepaths"]
        if filepaths.get("add_singles_to_folder") is not None:
            config.session.filepaths.add_singles_to_folder = filepaths["add_singles_to_folder"]
        if filepaths.get("folder_format") is not None:
            config.session.filepaths.folder_format = filepaths["folder_format"]
        if filepaths.get("track_format") is not None:
            config.session.filepaths.track_format = filepaths["track_format"]
        if filepaths.get("restrict_characters") is not None:
            config.session.filepaths.restrict_characters = filepaths["restrict_characters"]
        if filepaths.get("truncate_to") is not None:
            config.session.filepaths.truncate_to = filepaths["truncate_to"]

    if "conversions" in config_data:
        conversions = config_data["conversions"]
        if conversions.get("enabled") is not None:
            config.session.conversion.enabled = conversions["enabled"]
        if conversions.get("codec") is not None:
            config.session.conversion.codec = conversions["codec"]
        if conversions.get("sampling_rate") is not None:
            config.session.conversion.sampling_rate = conversions["sampling_rate"]
        if conversions.get("bit_depth") is not None:
            config.session.conversion.bit_depth = conversions["bit_depth"]
        if conversions.get("lossy_bitrate") is not None:
            config.session.conversion.lossy_bitrate = conversions["lossy_bitrate"]

    if "qobuz_filters" in config_data:
        qobuz_filters = config_data["qobuz_filters"]
        if qobuz_filters.get("extras") is not None:
            config.session.qobuz_filters.extras = qobuz_filters["extras"]
        if qobuz_filters.get("repeats") is not None:
            config.session.qobuz_filters.repeats = qobuz_filters["repeats"]
        if qobuz_filters.get("non_albums") is not None:
            config.session.qobuz_filters.non_albums = qobuz_filters["non_albums"]
        if qobuz_filters.get("features") is not None:
            config.session.qobuz_filters.features = qobuz_filters["features"]
        if qobuz_filters.get("non_studio_albums") is not None:
            config.session.qobuz_filters.non_studio_albums = qobuz_filters["non_studio_albums"]
        if qobuz_filters.get("non_remaster") is not None:
            config.session.qobuz_filters.non_remaster = qobuz_filters["non_remaster"]

    if "database" in config_data:
        database = config_data["database"]
        if database.get("downloads_enabled") is not None:
            config.session.database.downloads_enabled = database["downloads_enabled"]
        if database.get("downloads_path") is not None:
            config.session.database.downloads_path = database["downloads_path"]
        if database.get("failed_downloads_enabled") is not None:
            config.session.database.failed_downloads_enabled = database["failed_downloads_enabled"]
        if database.get("failed_downloads_path") is not None:
            config.session.database.failed_downloads_path = database["failed_downloads_path"]

    if "lastfm" in config_data:
        lastfm = config_data["lastfm"]
        if lastfm.get("source") is not None:
            config.session.lastfm.source = lastfm["source"]
        if lastfm.get("fallback_source") is not None:
            config.session.lastfm.fallback_source = lastfm["fallback_source"]

    if "cli" in config_data:
        cli = config_data["cli"]
        if cli.get("text_output") is not None:
            config.session.cli.text_output = cli["text_output"]
        if cli.get("progress_bars") is not None:
            config.session.cli.progress_bars = cli["progress_bars"]
        if cli.get("max_search_results") is not None:
            config.session.cli.max_search_results = cli["max_search_results"]

    if "misc" in config_data:
        misc = config_data["misc"]
        if misc.get("version") is not None:
            config.session.misc.version = misc["version"]
        if misc.get("check_for_updates") is not None:
            config.session.misc.check_for_updates = misc["check_for_updates"]

    # Update the TOML representation to reflect our changes
    config.session.update_toml()

    # Sync session changes to file config so downloads use the overridden values
    config.file.downloads.folder = config.session.downloads.folder
    config.file.downloads.source_subdirectories = config.session.downloads.source_subdirectories
    config.file.downloads.disc_subdirectories = config.session.downloads.disc_subdirectories
    config.file.downloads.concurrency = config.session.downloads.concurrency
    config.file.downloads.max_connections = config.session.downloads.max_connections
    config.file.downloads.requests_per_minute = config.session.downloads.requests_per_minute
    config.file.downloads.verify_ssl = config.session.downloads.verify_ssl

    # Sync artwork settings
    config.file.artwork.embed = config.session.artwork.embed
    config.file.artwork.embed_size = config.session.artwork.embed_size
    config.file.artwork.embed_max_width = config.session.artwork.embed_max_width
    config.file.artwork.save_artwork = config.session.artwork.save_artwork
    config.file.artwork.saved_max_width = config.session.artwork.saved_max_width

    # Sync other sections as needed...

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

def get_spotify_tracks(spotify_link: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """
    Get track information from Spotify link.
    
    Args:
        spotify_link: Spotify track or playlist link
        
    Returns:
        List of dictionaries with track information (artist and title)
    """
    # Load configuration from config.toml file
    config_data = load_config()

    # Set up Spotify client
    client_id = config_data.get("spotify", {}).get("client_id")
    client_secret = config_data.get("spotify", {}).get("client_secret")
    
    if not client_id or not client_secret:
        raise ValueError(
            "Spotify API credentials not found in mdl-config.toml.\n"
            "Please set client_id and client_secret in the [spotify] section of mdl-config.toml.\n"
            "Get them from: https://developer.spotify.com/dashboard/"
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
        return tracks, {'is_playlist': False, 'name': None}

    elif spotify_type == "playlist":
        # Get playlist name
        playlist_info = sp.playlist(spotify_id)
        playlist_name = playlist_info['name']

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

        return tracks, {'is_playlist': True, 'name': playlist_name}

    else:
        raise ValueError(f"Unsupported Spotify link type: {spotify_type}")

async def download_track_with_client(client, config, search_string: str, db=None, verbose: bool = False) -> Optional[str]:
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

async def download_multiple_tracks(tracks: List[Dict[str, str]], config_path: str = None, verbose: bool = False, is_playlist: bool = False, playlist_name: Optional[str] = None) -> None:
    """
    Download multiple tracks from Deezer based on artist and title information.
    
    Args:
        tracks: List of dictionaries with track information (artist and title)
        config_path: Path to streamrip config file
        verbose: Whether to print detailed output
    """
    # Load configuration from config.toml
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
    # Load configuration from config.toml
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
