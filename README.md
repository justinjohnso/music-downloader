# Music Downloader

A Python CLI tool for downloading music from Deezer based on search queries or Spotify links/URIs. This utility leverages Streamrip for downloading and Spotipy for handling Spotify links.

## Features

- Download individual tracks by searching artist and song name.
- Download entire Spotify playlists via URL or URI.
- Download individual Spotify tracks via URL or URI.
- Automatically embeds album artwork (via Streamrip).
- Cross-platform support (macOS, Windows, Linux).
- Verbose output option for detailed logging.

## Installation

### Prerequisites

- Python 3.8 or higher.
- `pipx` (for isolated environment installation):
  ```bash
  # Install pipx if you don't have it
  python3 -m pip install --user pipx
  # Add pipx to your PATH
  python3 -m pipx ensurepath
  ```
  *(Restart your terminal after running `ensurepath` if it's the first time)*
- Streamrip v2+ installed and configured with your Deezer ARL cookie.

### Install the Tool

Navigate to the project's root directory in your terminal:

```bash
cd /Users/justin/Library/CloudStorage/Dropbox/Code/projects/music-downloader
```

Install using `pipx`:

```bash
# Recommended: Install in editable mode for development
# Changes in the 'src' directory will be reflected immediately
pipx install --force -e .

# Or, install normally (less ideal for active development)
# pipx install --force .
```

## Usage

Once installed, the `music-downloader` command will be available globally.

```bash
# Download a track by search query
music-downloader "The Beatles - Hey Jude"

# Download a Spotify track URL
music-downloader "https://open.spotify.com/track/0aym2LBJBk9DAYuHHutrIl"

# Download a Spotify playlist URL
music-downloader "https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF"

# Download using Spotify URI
music-downloader "spotify:track:0aym2LBJBk9DAYuHHutrIl"

# Show verbose output during download
music-downloader --verbose "Daft Punk - One More Time"

# Specify a non-default streamrip config file
music-downloader -c ~/.config/streamrip/alternative_config.toml "query or link"

# Get help on command-line options
music-downloader --help
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

## Project Structure (src-layout)

*(Based on the setup for pipx installation)*

```
music-downloader/
├── src/
│   └── music_downloader/
│       ├── __init__.py        # Makes it a package
│       ├── cli.py             # Handles command-line arguments and execution flow
│       └── downloader.py      # Core logic for Spotify interaction and Streamrip calls
├── .env                     # Optional: Spotify credentials (should be in .gitignore)
├── .gitignore               # Specifies intentionally untracked files
├── pyproject.toml           # Build system configuration and project metadata (PEP 621)
└── README.md                # This file
```

## Requirements

Dependencies are managed in `pyproject.toml`:

- `streamrip>=2.0.0`
- `spotipy`
- `python-dotenv`
- `appdirs`

## Development

If you installed using `pipx install -e .`, any changes you make within the `src/music_downloader/` directory will be immediately reflected when you run the `music-downloader` command.

To update dependencies or project metadata, modify `pyproject.toml` and reinstall:

```bash
cd /Users/justin/Library/CloudStorage/Dropbox/Code/projects/music-downloader
pipx install --force -e .
```

## Troubleshooting

- **`Command not found: music-downloader`**: Ensure `pipx` installation completed successfully and that the `pipx` bin directory (`~/.local/bin` typically) is in your system's `PATH`. Run `python3 -m pipx ensurepath` and restart your terminal.
- **`Spotify API credentials not found`**: Verify your `.env` file exists in the correct location (home directory or execution directory) and contains the correct variable names (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`).
- **`Login failed` (Deezer)**: Check your Deezer ARL cookie in the Streamrip `config.toml` file. It might have expired.
- **Download Errors**: Use the `--verbose` flag to get more detailed error messages from Streamrip or Spotipy.

## License

MIT License
