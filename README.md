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

`pipx install .` creates two command shortcuts globally:
- **`mdl`** – Shorthand command
- **`music-downloader`** – Full command name

Both commands are available system-wide and work from any directory.

## Configuration

The `mdl-config.toml` file contains all Streamrip configuration variables. You can manage the entire Streamrip configuration through this TOML file instead of editing the streamrip config.toml directly.

### Setup

1. Copy `mdl-config-example.toml` to `mdl-config.toml` in your project root
2. Edit the values in `mdl-config.toml` as needed

```bash
cp mdl-config-example.toml mdl-config.toml
```

#### Spotify Credentials (Required for Spotify links)

```toml
[spotify]
client_id = "your_spotify_client_id"
client_secret = "your_spotify_client_secret"
```

**Where to get them:**
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Create or select an application
3. Find your Client ID and Client Secret
4. Add them to `mdl-config.toml`

#### Service Credentials

##### Deezer
```toml
[deezer]
arl = "your_deezer_arl_cookie"
quality = 1
lower_quality_if_not_available = true
use_deezloader = false
deezloader_warnings = true
```

**How to find your Deezer ARL:**
1. Open [Deezer Web Player](https://www.deezer.com/) and log in
2. Open your browser's Developer Tools (F12 or Cmd+Option+I)
3. Go to the **Application** or **Storage** tab
4. Navigate to **Cookies**
5. Find the cookie named `arl`
6. Copy its value and add to `mdl-config.toml`: `arl = "copied_value"`

##### Qobuz
```toml
[qobuz]
email_or_userid = "your_email_or_user_id"
password_or_token = "your_password_or_auth_token"
use_auth_token = false
app_id = "175774"
quality = 2
download_booklets = false
secrets = ""
```

##### Tidal
```toml
[tidal]
user_id = "your_user_id"
country_code = "your_country_code"
access_token = "your_access_token"
refresh_token = "your_refresh_token"
token_expiry = 0.0
quality = 2
download_videos = false
```

##### SoundCloud
```toml
[soundcloud]
client_id = "your_client_id"
app_version = "your_app_version"
quality = 0
```

##### YouTube
```toml
[youtube]
video_downloads_folder = "path/to/youtube/videos"
quality = 0
download_videos = false
```

#### Download Configuration
```toml
[downloads]
folder = "~/StreamripDownloads"
source_subdirectories = true
disc_subdirectories = true
concurrency = true
max_connections = 10
requests_per_minute = 60
verify_ssl = true
```

#### Artwork Configuration
```toml
[artwork]
embed = true
embed_size = "large"
embed_max_width = -1
save_artwork = false
saved_max_width = -1
```

#### Metadata Configuration
```toml
[metadata]
set_playlist_to_album = false
renumber_playlist_tracks = false
exclude = []
```

#### File Path Configuration
```toml
[filepaths]
add_singles_to_folder = false
folder_format = "{albumartist}/{album}"
track_format = "{tracknumber}. {title}"
restrict_characters = true
truncate_to = 120
```

#### Audio Conversion Configuration
```toml
[conversions]
enabled = false
codec = "FLAC"
sampling_rate = 48000
bit_depth = 16
lossy_bitrate = 320
```

#### Qobuz Filters
```toml
[qobuz_filters]
extras = true
repeats = true
non_albums = true
features = true
non_studio_albums = true
non_remaster = true
```

#### Database Configuration
```toml
[database]
downloads_enabled = true
downloads_path = "~/.local/share/streamrip/downloads.db"
failed_downloads_enabled = true
failed_downloads_path = "~/.local/share/streamrip/failed_downloads.db"
```

#### LastFM Configuration
```toml
[lastfm]
source = "lastfm"
fallback_source = "musicbrainz"
```

#### CLI Configuration
```toml
[cli]
text_output = true
progress_bars = true
max_search_results = 10
```

#### Miscellaneous Configuration
```toml
[misc]
version = "2.2.0"
check_for_updates = true
```

**Security Note:** Never commit the `mdl-config.toml` file to version control if it contains sensitive information like API keys or passwords. Add it to `.gitignore` if needed.

For detailed information about each configuration option, refer to the [Streamrip documentation](https://github.com/nathom/streamrip).

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

# Specify a non-default streamrip config file
mdl --config ~/.config/streamrip/alternative_config.toml "query or link"

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

### Alternative: Using Python Directly

If the `mdl` command isn't available:

```bash
python -m src.downloader "The Beatles - Hey Jude"
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
