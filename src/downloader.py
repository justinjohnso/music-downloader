import os
import sys
import argparse
import logging
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from streamrip.client import Client
from streamrip.config import Config
from streamrip.media import Song
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
        
        # Initialize the client with the preferred source
        client = Client(PREFERRED_SOURCE)
        
        # Search for the track
        results = client.search(search_query, "track")
        
        # If no results found
        if not results:
            logging.warning(f"No search results found for '{search_query}' on {PREFERRED_SOURCE}")
            return None
        
        # Get the first result which is usually the most relevant
        first_result = results[0]
        confidence = first_result.score if hasattr(first_result, 'score') else 0
        
        if confidence >= CONFIDENCE_THRESHOLD:
            logging.info(f"Match found ({PREFERRED_SOURCE}, Confidence: {confidence:.2f}): {first_result.title} by {first_result.artist}")
            
            # Create Song object and download
            song = Song(first_result.id, client)
            
            # Ensure output dir exists
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            
            # Download the song
            downloaded_file = song.download(output_dir=str(OUTPUT_DIR), skip_if_exists=True)
            
            if downloaded_file:
                downloaded_path = Path(downloaded_file)
                logging.info(f"SUCCESS ({PREFERRED_SOURCE}): {downloaded_path.name}")
                return downloaded_path
            else:
                logging.warning(f"Downloaded file path couldn't be determined for {search_query} ({PREFERRED_SOURCE})")
                return None
        else:
            logging.warning(f"Match found but confidence too low ({PREFERRED_SOURCE}, Confidence: {confidence:.2f}): {search_query}")
            
    except Exception as e:
        logging.error(f"Error during download attempt with {PREFERRED_SOURCE} for {search_query}: {e}", exc_info=True)

    # Attempt 2: Backup Source (Qobuz)
    if not downloaded_path:
        try:
            logging.info(f"Trying source: {BACKUP_SOURCE}")
            
            # Initialize the client with the backup source
            client = Client(BACKUP_SOURCE)
            
            # Search for the track
            results = client.search(search_query, "track")
            
            # If no results found
            if not results:
                logging.warning(f"No search results found for '{search_query}' on {BACKUP_SOURCE}")
                logging.error(f"Download FAILED for: {search_query} on both sources.")
                return None
            
            # Get the first result which is usually the most relevant
            first_result = results[0]
            confidence = first_result.score if hasattr(first_result, 'score') else 0
            
            if confidence >= CONFIDENCE_THRESHOLD:
                logging.info(f"Match found ({BACKUP_SOURCE}, Confidence: {confidence:.2f}): {first_result.title} by {first_result.artist}")
                
                # Create Song object and download
                song = Song(first_result.id, client)
                
                # Ensure output dir exists
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                
                # Download the song
                downloaded_file = song.download(output_dir=str(OUTPUT_DIR), skip_if_exists=True)
                
                if downloaded_file:
                    downloaded_path = Path(downloaded_file)
                    logging.info(f"SUCCESS ({BACKUP_SOURCE}): {downloaded_path.name}")
                    return downloaded_path
                else:
                    logging.warning(f"Downloaded file path couldn't be determined for {search_query} ({BACKUP_SOURCE})")
            else:
                logging.warning(f"Match found but confidence too low ({BACKUP_SOURCE}, Confidence: {confidence:.2f}): {search_query}")
                logging.error(f"Download FAILED for: {search_query} on both sources.")
                return None

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
        try:
            downloaded_path = download_track(track_info)
            if downloaded_path:
                successfully_downloaded_paths.append(downloaded_path)
        except Exception as e:
            print(f"Error processing track {i+1}: {e}")
            logging.error(f"Error processing track {i+1}: {e}", exc_info=True)
        # Add a small delay? Optional, might help avoid rate limiting if downloading many tracks.
        # import time
        # time.sleep(0.5)

    logging.info("--- Download Loop Finished ---")
    generate_m3u(successfully_downloaded_paths, OUTPUT_DIR)
    logging.info("--- Process Complete ---")

if __name__ == "__main__":
    main()

