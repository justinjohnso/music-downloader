import os
import sys
import argparse
import logging
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import asyncio # Add asyncio
# Imports based on the user-provided example
from streamrip.client import DeezerClient, QobuzClient
from streamrip.config import Config
from streamrip.media import Track, PendingTrack # Use Track/PendingTrack
# Assume these DB handler classes exist based on common patterns and error hint
from streamrip.db import Database, Dummy, Downloads, Failed # Corrected names
import appdirs # For finding config directory
import re # Import re for cleaning the search query

# --- Configuration ---
PREFERRED_SOURCE = "deezer"
BACKUP_SOURCE = "qobuz"
CONFIDENCE_THRESHOLD = 0.85
PLAYLIST_NAME = "downloaded_playlist.m3u"
APP_NAME = "music-downloader" # Used for this script's config/logs
CONFIG_DIR = Path(appdirs.user_config_dir(APP_NAME))
LOG_FILE = CONFIG_DIR / "downloader.log"
# Define the target Streamrip config file path
STREAMRIP_CONFIG_PATH = Path.home() / "Library/Application Support/streamrip/config.toml"

# --- Logging Setup ---
import logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to show all logs, including from Streamrip
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# --- Environment & Spotify Setup ---
def load_environment():
    """
    Loads environment variables from .env file.
    Searches in order (highest priority first):
    1. User's config directory (~/.config/music-downloader/.env)
    2. User's home directory (~/.env)
    3. Current working directory (.env)
    Variables found in higher priority locations override lower ones.
    """
    # Load in reverse order of priority, allowing overrides
    loaded_paths = []
    search_paths = [
        Path.cwd() / ".env",          # Lowest priority
        Path.home() / ".env",
        CONFIG_DIR / ".env"           # Highest priority
    ]

    for path in search_paths:
        if path.exists():
            # override=True ensures variables from higher-priority files overwrite lower ones
            if load_dotenv(dotenv_path=path, override=True, verbose=False):
                loaded_paths.append(str(path))
                logging.debug(f"Loaded environment variables from: {path}")

    if loaded_paths:
        # Log the highest priority file found (last one loaded)
        logging.info(f"Loaded .env variables (highest priority source: {loaded_paths[-1]}) ")
    else:
        logging.warning(f"No .env file found in standard locations ({CONFIG_DIR}, ~, CWD). Relying solely on environment variables.")

def get_spotify_client() -> spotipy.Spotify | None:
    """Initializes and returns a Spotipy client."""
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

    if not client_id or not client_secret:
        logging.error("Spotify API credentials (SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET) not found in .env file or environment.")
        return None

    try:
        client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        logging.info("Spotify client initialized successfully.")
        return sp
    except Exception as e:
        logging.error(f"Failed to initialize Spotify client: {e}", exc_info=True)
        return None

# --- Track Fetching Logic ---
def get_tracks_from_spotify(sp: spotipy.Spotify, url: str) -> list[dict]:
    """
    Fetches track information (name, artists) from a Spotify track or playlist URL.
    Returns a list of dictionaries, e.g., [{'name': 'Song Title', 'artists': ['Artist Name']}]
    """
    tracks_info = []
    try:
        if "track/" in url:
            print(f"Fetching single track info from: {url}")
            logging.info(f"Fetching single track info from: {url}")
            track = sp.track(url)
            if track:
                print(f"Found track: {track['name']} by {', '.join([artist['name'] for artist in track['artists']])}")
                tracks_info.append({
                    "name": track['name'],
                    "artists": [artist['name'] for artist in track['artists']]
                })
            else:
                print(f"Could not retrieve track info for: {url}")
                logging.warning(f"Could not retrieve track info for: {url}")

        elif "playlist/" in url:
            print(f"Fetching playlist info from: {url}")
            logging.info(f"Fetching playlist info from: {url}")
            offset = 0
            limit = 100 # Max limit per request
            while True:
                results = sp.playlist_items(url, limit=limit, offset=offset, fields='items(track(name, artists(name))),next')
                items = results['items']
                if not items:
                    break # No more items

                for item in items:
                    track = item.get('track')
                    if track and track.get('name') and track.get('artists'):
                        print(f"Found track: {track['name']} by {', '.join([artist['name'] for artist in track['artists']])}")
                        tracks_info.append({
                            "name": track['name'],
                            "artists": [artist['name'] for artist in track['artists']]
                        })
                    else:
                        print(f"Skipping item in playlist {url} due to missing track data: {item}")
                        logging.warning(f"Skipping item in playlist {url} due to missing track data: {item}")

                if results['next']:
                    offset += limit
                else:
                    break # No more pages
        else:
            print(f"Invalid Spotify URL provided: {url}. Must contain 'track/' or 'playlist/'.")
            logging.error(f"Invalid Spotify URL provided: {url}. Must contain 'track/' or 'playlist/'.")

    except spotipy.exceptions.SpotifyException as e:
        print(f"Spotify API error fetching URL {url}: {e}")
        logging.error(f"Spotify API error fetching URL {url}: {e}")
    except Exception as e:
        print(f"Unexpected error fetching Spotify data for {url}: {e}")
        logging.error(f"Unexpected error fetching Spotify data for {url}: {e}", exc_info=True)

    print(f"Found {len(tracks_info)} tracks from Spotify URL.")
    logging.info(f"Found {len(tracks_info)} tracks from Spotify URL.")
    return tracks_info

# --- Downloading Logic ---
# download_track function remains largely the same, ensuring it receives
# the streamrip_config and the dummy db object. The search result parsing
# fix (accessing list[0]) is kept.

async def download_track(track_info: dict, config: Config, db: Database) -> Path | None:
    """
    Attempts to download a single track using Streamrip client objects, preferring Deezer then Qobuz.
    Returns the Path object of the downloaded file if successful, otherwise None.
    """
    track_name = track_info['name']
    artist_names = ", ".join(track_info['artists'])
    # Original query for logging
    original_search_query = f"{artist_names} - {track_name}"
    # REMOVED: search_query = re.sub(r'[^\w\s]+', '', original_search_query).lower()
    # Use the original query directly
    search_query = original_search_query
    logging.info(f"Attempting download for: {original_search_query} (Using query: '{search_query}')") # Updated log

    downloaded_path = None

    # --- Attempt 1: Preferred Source (Deezer) ---
    client = None
    try:
        logging.info(f"Trying source: {PREFERRED_SOURCE}")
        client = DeezerClient(config)
        await client.login()
        if not client.logged_in:
            logging.error(f"Failed to log in to {PREFERRED_SOURCE}. Check ARL in config file. Skipping.")
        else:
            logging.info(f"Logged in to {PREFERRED_SOURCE} successfully.")
            search_result_list = await client.search(query=search_query, media_type="track")
            logging.debug(f"Raw Deezer search result list: {search_result_list}")
            if not search_result_list or not isinstance(search_result_list, list) or not search_result_list[0] or 'data' not in search_result_list[0] or not search_result_list[0]['data']:
                logging.warning(f"No search results found or unexpected format for '{search_query}' on {PREFERRED_SOURCE}")
            else:
                search_result_dict = search_result_list[0]
                first_result_data = search_result_dict['data'][0]
                result_title = first_result_data.get('title', '').lower()
                result_artist = first_result_data.get('artist', {}).get('name', '').lower()
                spotify_title = track_name.lower()
                spotify_artists_lower = [a.lower() for a in track_info['artists']]
                title_match = result_title == spotify_title
                artist_match = result_artist in spotify_artists_lower
                if title_match and artist_match:
                    track_id = first_result_data.get('id')
                    album_data = first_result_data.get('album')
                    album_id = album_data.get('id') if album_data else None
                    if track_id and album_id:
                        try:
                            from streamrip.media import PendingAlbum
                            pending_album = PendingAlbum(
                                id=album_id,
                                client=client,
                                config=config,
                                db=db
                            )
                            resolved_album = await pending_album.resolve()
                            pending_track = PendingTrack(
                                id=track_id,
                                client=client,
                                config=config,
                                folder=config.session.downloads.folder,  # Use config.session.downloads.folder
                                db=db,
                                cover_path="",
                                album=resolved_album.meta
                            )
                            resolved_track = await pending_track.resolve()
                            if resolved_track:
                                rip_result = await resolved_track.rip()
                                if rip_result and rip_result.exists():
                                    downloaded_path = rip_result
                                    logging.info(f"Download SUCCEEDED ({PREFERRED_SOURCE}): {downloaded_path}")
                                    db.downloads.add(track_id, PREFERRED_SOURCE)
                                else:
                                    logging.error(f"Rip command finished but no file found for {original_search_query} ({PREFERRED_SOURCE})")
                                    db.failed.add(track_id, PREFERRED_SOURCE)
                        except Exception as e:
                            logging.error(f"Error processing PendingTrack for {track_id} ({PREFERRED_SOURCE}): {e}", exc_info=True)
                            db.failed.add(track_id, PREFERRED_SOURCE)
                    else:
                        logging.warning(f"Match found ({PREFERRED_SOURCE}) but track ID or album data missing in result.")
                else:
                    logging.warning(f"No exact match found ({PREFERRED_SOURCE}, Title Match: {title_match}, Artist Match: {artist_match}) for: {original_search_query}. Result: {result_title} by {result_artist}")
    except Exception as e:
        logging.error(f"Error during download attempt with {PREFERRED_SOURCE} for {original_search_query}: {e}", exc_info=True)
    finally:
        if client and hasattr(client, 'close') and not getattr(client, 'closed', True):
            try:
                await client.close()
                logging.debug(f"Closed {PREFERRED_SOURCE} client session in finally block.")
            except Exception as close_err:
                logging.error(f"Error closing {PREFERRED_SOURCE} client in finally block: {close_err}", exc_info=True)


    # --- Attempt 2: Backup Source (Qobuz) ---
    if not downloaded_path:
        client = None
        try:
            logging.info(f"Trying source: {BACKUP_SOURCE}")
            qobuz_creds_present = (hasattr(config, 'session') and
                                 hasattr(config.session, 'qobuz') and
                                 config.session.qobuz.email_or_userid and
                                 config.session.qobuz.password_or_token)
            if not qobuz_creds_present:
                logging.warning(f"Qobuz credentials not found in loaded config. Skipping Qobuz.")
                pass
            else:
                client = QobuzClient(config)
                await client.login()
                if not client.logged_in:
                    logging.error(f"Failed to log in to {BACKUP_SOURCE}. Check credentials in config file. Skipping.")
                else:
                    logging.info(f"Logged in to {BACKUP_SOURCE} successfully.")
                    search_result_list = await client.search(query=search_query, media_type="track")
                    logging.debug(f"Raw Qobuz search result list: {search_result_list}")
                    if (not search_result_list or not isinstance(search_result_list, list) or not search_result_list[0] or
                            'tracks' not in search_result_list[0] or 'items' not in search_result_list[0]['tracks'] or
                            not search_result_list[0]['tracks']['items']):
                        logging.warning(f"No search results found or unexpected format for '{search_query}' on {BACKUP_SOURCE}")
                    else:
                        search_result_dict = search_result_list[0]
                        first_result_data = search_result_dict['tracks']['items'][0]
                        result_title = first_result_data.get('title', '').lower()
                        result_artist = first_result_data.get('performer', {}).get('name', '').lower()
                        spotify_title = track_name.lower()
                        spotify_artists_lower = [a.lower() for a in track_info['artists']]
                        title_match = result_title == spotify_title
                        artist_match = result_artist in spotify_artists_lower
                        if title_match and artist_match:
                            track_id = first_result_data.get('id')
                            album_data = first_result_data.get('album')
                            album_id = album_data.get('id') if album_data else None
                            if track_id and album_id:
                                try:
                                    from streamrip.media import PendingAlbum
                                    pending_album = PendingAlbum(
                                        id=album_id,
                                        client=client,
                                        config=config,
                                        db=db
                                    )
                                    resolved_album = await pending_album.resolve()
                                    pending_track = PendingTrack(
                                        id=track_id,
                                        client=client,
                                        config=config,
                                        folder=config.session.downloads.folder,  # Use config.session.downloads.folder
                                        db=db,
                                        cover_path="",
                                        album=resolved_album.meta
                                    )
                                    resolved_track = await pending_track.resolve()
                                    if resolved_track:
                                        rip_result = await resolved_track.rip()
                                        if rip_result and rip_result.exists():
                                            downloaded_path = rip_result
                                            logging.info(f"Download SUCCEEDED ({BACKUP_SOURCE}): {downloaded_path}")
                                            db.downloads.add(track_id, BACKUP_SOURCE)
                                        else:
                                            logging.error(f"Rip command finished but no file found for {original_search_query} ({BACKUP_SOURCE})")
                                            db.failed.add(track_id, BACKUP_SOURCE)
                                except Exception as e:
                                    logging.error(f"Error processing PendingTrack for {track_id} ({BACKUP_SOURCE}): {e}", exc_info=True)
                                    db.failed.add(track_id, BACKUP_SOURCE)
                            else:
                                logging.warning(f"Match found ({BACKUP_SOURCE}) but track ID or album data missing in result.")
                        else:
                            logging.warning(f"No exact match found ({BACKUP_SOURCE}, Title Match: {title_match}, Artist Match: {artist_match}) for: {original_search_query}. Result: {result_title} by {result_artist}")
        except Exception as e:
            logging.error(f"Error during download attempt with {BACKUP_SOURCE} for {original_search_query}: {e}", exc_info=True)
        finally:
            if client and hasattr(client, 'close') and not getattr(client, 'closed', True):
                try:
                    await client.close()
                    logging.debug(f"Closed {BACKUP_SOURCE} client session in finally block.")
                except Exception as close_err:
                    logging.error(f"Error closing {BACKUP_SOURCE} client in finally block: {close_err}", exc_info=True)

    if not downloaded_path:
         # Log failure only if both sources were tried (or Qobuz was skipped due to missing creds after Deezer failed)
         logging.error(f"Download FAILED for: {original_search_query} on available sources.")

    return downloaded_path


# --- Playlist Generation ---
def generate_m3u(downloaded_files: list[Path], output_dir: Path):
    """Generates an M3U playlist file for the downloaded tracks."""
    if not downloaded_files:
        logging.info("No new files were downloaded, skipping M3U playlist generation.")
        return

    m3u_path = output_dir / PLAYLIST_NAME
    logging.info(f"Generating M3U playlist at: {m3u_path}")

    try:
        with open(m3u_path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for file_path in downloaded_files:
                # Use relative paths within the M3U file for portability
                try:
                    relative_path = file_path.relative_to(output_dir)
                    f.write(f"{relative_path.as_posix()}\n") # Use POSIX paths (forward slashes)
                except ValueError:
                     # Should not happen if files are in output_dir, but handle defensively
                     logging.warning(f"Could not make path relative for M3U: {file_path}. Using absolute path.")
                     f.write(f"{file_path.as_posix()}\n")

        logging.info(f"Successfully generated M3U playlist with {len(downloaded_files)} entries.")
    except Exception as e:
        logging.error(f"Failed to generate M3U playlist: {e}", exc_info=True)


# --- Main Execution ---
def main():
    """Main function to parse arguments and orchestrate the download process."""
    parser = argparse.ArgumentParser(description="Download Spotify tracks/playlists using Streamrip.")
    parser.add_argument("url", help="Spotify track or playlist URL.")
    args = parser.parse_args()

    logging.info("--- Starting Download Process ---")
    # Keep using appdirs for this script's specific logs/config if needed
    logging.info(f"Using script config directory: {CONFIG_DIR}")

    # Attempt to load Streamrip Config from file
    streamrip_config = None
    if STREAMRIP_CONFIG_PATH.exists():
        try:
            streamrip_config = Config(STREAMRIP_CONFIG_PATH)
            logging.info(f"Streamrip config loaded from: {STREAMRIP_CONFIG_PATH}")
            # --- ADDED DEBUG LOGGING ---
            logging.debug(f"dir(streamrip_config): {dir(streamrip_config)}")
            logging.debug(f"repr(streamrip_config): {repr(streamrip_config)}")
            # --- END ADDED DEBUG LOGGING ---
            if hasattr(streamrip_config, 'database'):
                logging.debug(f"Loaded streamrip_config.database section: {streamrip_config.database}")
            else:
                logging.debug("streamrip_config has no 'database' attribute.")
            # --- END ADDED DEBUG LOGGING ---
        except Exception as e:
            logging.warning(f"Found config at {STREAMRIP_CONFIG_PATH} but failed to load ({type(e).__name__}: {e}). Falling back to defaults.")
            streamrip_config = Config.defaults()
            logging.info("Streamrip config initialized from default location.")
    else:
        logging.warning(f"Streamrip config file not found at: {STREAMRIP_CONFIG_PATH}. Falling back to defaults.")
        streamrip_config = Config.defaults()
        logging.info("Streamrip config initialized from default location.")

    # Use config.session.downloads.folder for output_dir
    output_dir = Path(streamrip_config.session.downloads.folder)
    logging.info(f"Using output directory: {output_dir}")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Output directory ensured: {output_dir}")
    except Exception as e:
        logging.error(f"Could not create output directory {output_dir}: {e}")
        sys.exit(1)

    load_environment() # Still load .env for Spotify creds

    # --- Initialize Database using Dummy handlers (as per example) ---
    try:
        db = Database(downloads=Dummy(), failed=Dummy())
        logging.info("Initialized Streamrip Database with Dummy handlers (as per scripting example).")
    except Exception as e:
        # This shouldn't fail, but include for safety
        logging.error(f"Failed to initialize Dummy Database ({type(e).__name__}: {e}). Exiting.", exc_info=True)
        sys.exit(1)
    # --- End Database Initialization ---

    sp = get_spotify_client()

    if not sp:
        sys.exit(1)

    tracks_to_download = get_tracks_from_spotify(sp, args.url)

    if not tracks_to_download:
        logging.info("No tracks found or retrieved from Spotify URL. Exiting.")
        sys.exit(0)

    successfully_downloaded_paths = []
    for i, track_info in enumerate(tracks_to_download):
        logging.info(f"--- Processing track {i+1}/{len(tracks_to_download)} ---")
        try:
            # Pass the loaded config and dummy db to the async function
            downloaded_path = asyncio.run(download_track(track_info, streamrip_config, db))
            if downloaded_path:
                successfully_downloaded_paths.append(downloaded_path)
        except Exception as e:
            print(f"Error processing track {i+1}: {e}")
            logging.error(f"Error processing track {i+1}: {e}", exc_info=True)
        # Optional delay - use time.sleep for synchronous main
        # import time
        # time.sleep(0.5)

    logging.info("--- Download Loop Finished ---")
    # When generating the M3U playlist, use config.output_dir
    generate_m3u(successfully_downloaded_paths, output_dir)
    logging.info("--- Process Complete ---")

if __name__ == "__main__":
    main()

