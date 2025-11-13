# Music Downloader

A Python CLI tool that extends [streamrip](https://github.com/nathom/streamrip) for downloading music from Deezer (with Qobuz fallback) based on search queries or Spotify links/URIs.

This tool allows users to:
- Search for and download individual tracks from Deezer or Qobuz
- Process Spotify track or playlist links/URIs:
  - Extracts track information (artist, title) using the Spotify API
  - Searches for the corresponding tracks on Deezer (falling back to Qobuz)
  - Downloads the found tracks using Streamrip
  - Generates an M3U playlist file in the download directory when a Spotify playlist is processed

It utilizes:
- `streamrip` for handling the actual download and interaction with Deezer/Qobuz
- `spotipy` for interacting with the Spotify Web API
- `tomlkit` for configuration file parsing
- `asyncio` for concurrent downloads

## Features

- Download individual tracks by searching artist and song name (Deezer/Qobuz)
- Download entire Spotify playlists via URL or URI (searches Deezer/Qobuz)
- Download individual Spotify tracks via URL or URI (searches Deezer/Qobuz)
- Generates `.m3u` playlist file for downloaded Spotify playlists
- Qobuz fallback if tracks aren't found on Deezer
- Automatically embeds album artwork (via Streamrip)
- Cross-platform support (macOS, Windows, Linux)
- Verbose output option for detailed logging

## Supported Commands

This tool supports two modes:

### CLI Mode (Command Line)
Run with arguments for terminal usage:

1. **Search queries**: Simple text like `"Artist - Song Title"` for downloading individual tracks
2. **Spotify links/URIs**: URLs or URIs for Spotify tracks or playlists
3. **Verbose option**: Add `--verbose` for detailed output

### GUI Mode (Graphical Interface)
Run `mdl --gui` or `mdl-gui` to launch a user-friendly graphical interface with input fields for queries, verbose options, and a config tab to modify all download settings.

**Note**: This is a simplified wrapper around streamrip. For advanced commands like searching by artist, album, or specific sources (e.g., `rip search deezer artist "Red Hot Chili Peppers"`), use streamrip directly since it's installed as a dependency.

## Installation

### Prerequisites

- Python 3.10 or higher
- `pipx` (for system-wide CLI installation)

### Quick Setup

1. Install `pipx` if you don't have it:
   ```bash
   brew install pipx
   ```

2. Clone and navigate to the project directory:
   ```bash
   git clone https://github.com/justinjohnso/music-downloader.git
   cd music-downloader
   ```

3. Install globally with pipx:
   ```bash
   pipx install .
   ```

4. Configure the tool by copying and editing the config file:
   ```bash
   cp mdl-config-example.toml mdl-config.toml
   # Edit mdl-config.toml with your credentials and preferences
   ```

`pipx install .` creates three command shortcuts globally:
- **`mdl`** – Shorthand CLI command
- **`mdl-gui`** – GUI launcher
- **`music-downloader`** – Full CLI command name

Both commands are available system-wide and work from any directory.

## Configuration

The `mdl-config.toml` file allows you to override all streamrip configuration options.

### Quick Setup

1. Copy the example config: `cp mdl-config-example.toml mdl-config.toml`
2. Edit `mdl-config.toml` with your credentials and preferences

### Required: Spotify Credentials (for Spotify links)

```toml
[spotify]
client_id = "your_spotify_client_id"
client_secret = "your_spotify_client_secret"
```

Get these from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).

### Required: Service Credentials

At minimum, set up Deezer or Qobuz credentials in the `[deezer]` or `[qobuz]` sections. See `mdl-config-example.toml` for all options and detailed setup instructions for each service (Deezer ARL, Qobuz login, etc.).

### Optional: Download Settings

Customize download behavior in the `[downloads]`, `[artwork]`, `[filepaths]`, and other sections. All streamrip options are supported - see `mdl-config-example.toml` for the full list.

**Security Note:** Never commit `mdl-config.toml` to version control if it contains sensitive credentials.

## Usage

After installation, use the `mdl` shorthand command:

```bash
# Download a track by search query
mdl "The Beatles - Hey Jude"

# Download a Spotify track URL
mdl "https://open.spotify.com/track/0aym2LBJBk9DAYuHHutrIl"

# Download a Spotify playlist URL
mdl "https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF"

# Download using Spotify URI
mdl "spotify:track:0aym2LBJBk9DAYuHHutrIl"

# Show verbose output during download
mdl --verbose "Daft Punk - One More Time"

# Launch GUI
mdl --gui
# or
mdl-gui

# Get help on command-line options
mdl --help
```

### Alternative: Using Python Directly

If the `mdl` command isn't available:

```bash
python -m src.downloader "The Beatles - Hey Jude"
```

Or use the longer command name:

```bash
music-downloader "The Beatles - Hey Jude"
```

## Dependencies

- `streamrip>=2.0.0` – Handles Deezer/Qobuz downloads
- `spotipy` – Spotify Web API client
- `tomlkit` – Configuration file parsing
- `appdirs` – Platform-specific directory paths

Install all with: `pip install -r requirements.txt`

## Troubleshooting

**"mdl: command not found"**
- Ensure you installed with `pipx install .`
- Check installation: `pipx list | grep music-downloader`
- Verify pipx is in your PATH: `echo $PATH | grep .local/bin`
- Reinstall: `pipx uninstall music-downloader && pipx install .`

**"Spotify API credentials not found"**
- Ensure `mdl-config.toml` file exists and contains the `[spotify]` section
- Check that `client_id` and `client_secret` are set correctly in `mdl-config.toml`
- Verify the values aren't empty (get them from [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/))

**"Login failed" (Deezer)**
- Check if `arl` is set correctly in the `[deezer]` section of `mdl-config.toml`
- Deezer ARL cookies can expire; get a new one from the browser as described in the configuration section

**Download Errors**
- Use the `--verbose` flag for detailed error messages
- Check [streamrip docs](https://github.com/nathom/streamrip) for more information

## License

MIT License
