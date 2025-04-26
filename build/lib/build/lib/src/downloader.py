import os
import sys
import argparse
import logging
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from streamrip.api import rip, RipStatus, RipResult
import appdirs # For finding config directory

# --- Configuration ---
OUTPUT_DIR = Path("Output") # Output relative to current working directory
PREFERRED_SOURCE = "deezer"
BACKUP_SOURCE = "qobuz"
CONFIDENCE_THRESHOLD = 0.85
PLAYLIST_NAME = "downloaded_playlist.m3u"
APP_NAME = "music-downloader" # Used for config directory
CONFIG_DIR = Path(appdirs.user_config_dir(APP_NAME))
LOG_FILE = CONFIG_DIR / "downloader.log"

# --- Logging Setup ---
# Ensure config directory exists for logging
try:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
except OSError as e:
    # Fallback to logging only to console if config dir fails
    print(f"Warning: Could not create config directory {CONFIG_DIR}. Log file disabled. Error: {e}", file=sys.stderr)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
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
            logging.info(f"Fetching single track info from: {url}")
            track = sp.track(url)
            if track:
                tracks_info.append({
                    "name": track['name'],
                    "artists": [artist['name'] for artist in track['artists']]
                })
            else:
                logging.warning(f"Could not retrieve track info for: {url}")

        elif "playlist/" in url:
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
                    # Handle cases where track might be None (e.g., local files in playlist)
                    if track and track.get('name') and track.get('artists'):
                         tracks_info.append({
                            "name": track['name'],
                            "artists": [artist['name'] for artist in track['artists']]
                        })
                    else:
                        logging.warning(f"Skipping item in playlist {url} due to missing track data: {item}")

                if results['next']:
                    offset += limit
                else:
                    break # No more pages
        else:
            logging.error(f"Invalid Spotify URL provided: {url}. Must contain 'track/' or 'playlist/'.")

    except spotipy.exceptions.SpotifyException as e:
        logging.error(f"Spotify API error fetching URL {url}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error fetching Spotify data for {url}: {e}", exc_info=True)

    logging.info(f"Found {len(tracks_info)} tracks from Spotify URL.")
    return tracks_info

# --- Downloading Logic ---
def download_track(track_info: dict) -> Path | None:
    """
    Attempts to download a single track using Streamrip, preferring Deezer then Qobuz.
    Returns the Path object of the downloaded file if successful, otherwise None.
    """
    track_name = track_info['name']
    # Join multiple artists with ", "
    artist_names = ", ".join(track_info['artists'])
    search_query = f"{artist_names} - {track_name}"
    logging.info(f"Attempting download for: {search_query}")

    downloaded_path = None

    # Attempt 1: Preferred Source (Deezer)
    try:
        logging.info(f"Trying source: {PREFERRED_SOURCE}")
        result: RipResult = rip(
            query=search_query,
            source=PREFERRED_SOURCE,
            output_path=OUTPUT_DIR,
            skip_existing=True, # Don't redownload if file exists
            # We check confidence manually below
        )

        if result.status == RipStatus.SUCCESS and result.confidence >= CONFIDENCE_THRESHOLD:
            if result.files:
                downloaded_path = result.files[0].path # Assuming one file per track download
                logging.info(f"SUCCESS ({PREFERRED_SOURCE}, Confidence: {result.confidence:.2f}): {downloaded_path.name}")
                return downloaded_path
            else:
                 logging.warning(f"SUCCESS status but no files reported for {search_query} ({PREFERRED_SOURCE})")
        elif result.status == RipStatus.ALREADY_EXISTS:
             logging.info(f"ALREADY EXISTS: {search_query} (Skipping download attempt)")
             # We need to figure out the path if it already exists.
             # This is tricky as streamrip doesn't easily return it in this case.
             # For now, we won't add pre-existing files to the M3U.
             # A possible improvement: search the output dir for a matching file.
             return None # Indicate not newly downloaded for playlist generation
        else:
            logging.warning(f"Failed ({PREFERRED_SOURCE}, Status: {result.status.name}, Confidence: {result.confidence:.2f}): {search_query}")

    except Exception as e:
        logging.error(f"Error during download attempt with {PREFERRED_SOURCE} for {search_query}: {e}", exc_info=True)

    # Attempt 2: Backup Source (Qobuz)
    if not downloaded_path:
        try:
            logging.info(f"Trying source: {BACKUP_SOURCE}")
            result: RipResult = rip(
                query=search_query,
                source=BACKUP_SOURCE,
                output_path=OUTPUT_DIR,
                skip_existing=True,
            )

            if result.status == RipStatus.SUCCESS and result.confidence >= CONFIDENCE_THRESHOLD:
                 if result.files:
                    downloaded_path = result.files[0].path
                    logging.info(f"SUCCESS ({BACKUP_SOURCE}, Confidence: {result.confidence:.2f}): {downloaded_path.name}")
                    return downloaded_path
                 else:
                    logging.warning(f"SUCCESS status but no files reported for {search_query} ({BACKUP_SOURCE})")
            elif result.status == RipStatus.ALREADY_EXISTS:
                 logging.info(f"ALREADY EXISTS: {search_query} (Skipping download attempt)")
                 return None # Indicate not newly downloaded
            else:
                logging.warning(f"Failed ({BACKUP_SOURCE}, Status: {result.status.name}, Confidence: {result.confidence:.2f}): {search_query}")
                logging.error(f"Download FAILED for: {search_query} on both sources.")
                return None # Failed on both

        except Exception as e:
            logging.error(f"Error during download attempt with {BACKUP_SOURCE} for {search_query}: {e}", exc_info=True)
            logging.error(f"Download FAILED for: {search_query} due to error on backup source.")
            return None # Failed on both

    return None # Should not be reached if logic is correct, but ensures return

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
    logging.info(f"Using config directory: {CONFIG_DIR}")
    # Log the absolute path for clarity, as CWD will vary
    logging.info(f"Using output directory: {OUTPUT_DIR.resolve()}")
    logging.info(f"Input URL: {args.url}")

    load_environment()
    sp = get_spotify_client()

    if not sp:
        sys.exit(1) # Exit if Spotify client failed

    # Ensure output directory exists
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        logging.info(f"Output directory ensured: {OUTPUT_DIR}")
    except OSError as e:
        logging.error(f"Could not create output directory {OUTPUT_DIR}: {e}")
        sys.exit(1)

    tracks_to_download = get_tracks_from_spotify(sp, args.url)

    if not tracks_to_download:
        logging.info("No tracks found or retrieved from Spotify URL. Exiting.")
        sys.exit(0)

    successfully_downloaded_paths = []
    for i, track_info in enumerate(tracks_to_download):
        logging.info(f"--- Processing track {i+1}/{len(tracks_to_download)} ---")
        downloaded_path = download_track(track_info)
        if downloaded_path:
            successfully_downloaded_paths.append(downloaded_path)
        # Add a small delay? Optional, might help avoid rate limiting if downloading many tracks.
        # import time
        # time.sleep(0.5)

    logging.info("--- Download Loop Finished ---")
    generate_m3u(successfully_downloaded_paths, OUTPUT_DIR)
    logging.info("--- Process Complete ---")

if __name__ == "__main__":
    main()

