# Music Downloader

A Python CLI tool for downloading music from Deezer (with Qobuz fallback) based on search queries or Spotify links/URIs. 

This script allows users to:
- Search for and download individual tracks from Deezer or Qobuz.
- Process Spotify track or playlist links/URIs:
    - Extracts track information (artist, title) using the Spotify API.
    - Searches for the corresponding tracks on Deezer (falling back to Qobuz).
    - Downloads the found tracks using Streamrip.
    - Generates an M3U playlist file in the download directory when a Spotify playlist is processed.

It utilizes:
- `streamrip` for handling the actual download and interaction with Deezer/Qobuz.
- `spotipy` for interacting with the Spotify Web API.
- `python-dotenv` for managing Spotify API credentials.
- `asyncio` for concurrent downloads.

## Features

- Download individual tracks by searching artist and song name (Deezer/Qobuz).
- Download entire Spotify playlists via URL or URI (searches Deezer/Qobuz).
- Download individual Spotify tracks via URL or URI (searches Deezer/Qobuz).
- Generates `.m3u` playlist file for downloaded Spotify playlists.
- Qobuz fallback if tracks aren't found on Deezer.
- Automatically embeds album artwork (via Streamrip).
- Cross-platform support (macOS, Windows, Linux).
- Verbose output option for detailed logging.

## Installation

### Prerequisites

- Python 3.8 or higher.
- `pip` (Python's package installer, usually included with Python).
- Streamrip v2+ installed and configured with your Deezer ARL cookie.

### Install Dependencies

1.  Clone or download this repository.
2.  Navigate to the project's root directory in your terminal:
    ```bash
    cd /path/to/music-downloader
    ```
3.  Create and activate a virtual environment (Recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\\Scripts\\activate`
    ```
4.  Install the required Python packages:
    ```bash
    python -m pip install -r requirements.txt
    ```

## Usage

Run the script directly using Python from the project's root directory (ensure your virtual environment is active):

```bash
# Download a track by search query
python music-downloader.py "The Beatles - Hey Jude"

# Download a Spotify track URL
python music-downloader.py "https://open.spotify.com/track/0aym2LBJBk9DAYuHHutrIl"

# Download a Spotify playlist URL
python music-downloader.py "https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF"

# Download using Spotify URI
python music-downloader.py "spotify:track:0aym2LBJBk9DAYuHHutrIl"

# Show verbose output during download
python music-downloader.py --verbose "Daft Punk - One More Time"

# Specify a non-default streamrip config file
python music-downloader.py -c ~/.config/streamrip/alternative_config.toml "query or link"

# Get help on command-line options
python music-downloader.py --help
```

## Configuration

### 1. Streamrip Configuration

This tool relies on your existing Streamrip configuration file for Deezer login (ARL cookie) and download settings (path, quality, etc.). It automatically detects the default location:

- **macOS**: `~/Library/Application Support/streamrip/config.toml`
- **Windows**: `%APPDATA%\streamrip\config.toml`
- **Linux**: `~/.config/streamrip/config.toml`

Ensure Streamrip is configured correctly. You can override the config file path using the `-c` or `--config` option.

**Tip:** To prevent Streamrip from creating `Disc 1` subfolders, run:
`streamrip config set downloads.disc_subdirectories false`

### 2. Spotify API Credentials

Required **only** when using Spotify links or URIs.

1.  Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and create an application (or use an existing one).
2.  Note down your **Client ID** and **Client Secret**.
3.  Create a file named `.env` either in your **home directory** (`~/.env`) or in the directory **where you run the `music-downloader` command**.
4.  Add your credentials to the `.env` file:

    ```dotenv
    # Example .env file content
    SPOTIFY_CLIENT_ID='YOUR_SPOTIFY_CLIENT_ID'
    SPOTIFY_CLIENT_SECRET='YOUR_SPOTIFY_CLIENT_SECRET'
    ```

    *(The tool also recognizes `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET`)*

## Project Structure

```
music-downloader/
├── music-downloader.py    # The main script
├── requirements.txt       # Project dependencies
├── .env                   # Optional: Spotify credentials (should be in .gitignore)
├── .gitignore             # Specifies intentionally untracked files
└── README.md              # This file
```

## Requirements

Dependencies are listed in `requirements.txt`. Install them using:
`pip install -r requirements.txt`

- `streamrip>=2.0.0`
- `spotipy`
- `python-dotenv`
- `appdirs` # Note: appdirs might be implicitly required by streamrip

## Development

Modify the `music-downloader.py` script directly. If you add new dependencies, update `requirements.txt`:

```bash
# Activate your virtual environment first
pip freeze > requirements.txt
```

## Troubleshooting

- **`Command not found: python` or `ImportError`**: Ensure you have activated the virtual environment (`source venv/bin/activate`) before running the script. Make sure dependencies were installed correctly (`pip install -r requirements.txt`).
- **`Spotify API credentials not found`**: Verify your `.env` file exists in the correct location (home directory or the directory where you run `python music-downloader.py`) and contains the correct variable names (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`).
- **`Login failed` (Deezer)**: Check your Deezer ARL cookie in the Streamrip `config.toml` file. It might have expired.
- **Download Errors**: Use the `--verbose` flag to get more detailed error messages from Streamrip or Spotipy.

## License

MIT License
