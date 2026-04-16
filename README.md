# Music Downloader

A Python CLI and GUI tool for downloading high-quality music tracks from Deezer (with Qobuz fallback) based on search queries or Spotify links.

## Quick Start

1. **Install pipx** (if you don't have it):
   ```bash
   brew install pipx
   ```

2. **Clone and install**:
   ```bash
   git clone --recursive https://github.com/justinjohnso/music-downloader.git
   cd music-downloader
   pipx install .
   ```

3. **Run the setup wizard** — it will walk you through Deezer login, download folder, and quality settings:
   ```bash
   mdl --setup
   ```

## Usage

### CLI
```bash
# Search and download a track
mdl "The Beatles - Hey Jude"

# Download a Spotify track (requires Spotify credentials in config)
mdl "https://open.spotify.com/track/..."

# Download an entire Spotify playlist (generates an M3U file)
mdl "https://open.spotify.com/playlist/..."

# Run with detailed output
mdl --verbose "Artist - Track"
```

### GUI
Launch the graphical interface for a user-friendly experience:
```bash
mdl-gui
```

## Configuration

The `mdl-config.toml` file is searched in the following locations (in order):
1. Current working directory
2. User's home directory (`~/mdl-config.toml`)
3. Platform Application Support folder (e.g., `~/Library/Application Support/music-downloader/` on macOS).

### Spotify Credentials
To resolve Spotify links, you must provide your own API credentials in `mdl-config.toml`:

```toml
[spotify]
client_id = "your-client-id"
client_secret = "your-client-secret"
```
Get them from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).

### Deezer ARL
To download from Deezer, you need an ARL cookie from your account. The setup wizard will ask for it and explain where to find it. ARLs expire every 3-4 months; when login fails, grab a fresh one and run `mdl --setup` again.

## Troubleshooting

**"mdl: command not found"**
- Ensure `pipx` is in your PATH. Try running `pipx ensurepath` and restarting your terminal.

**"Login failed" (Deezer)**
- Your Deezer ARL has likely expired. Get a new one from the browser and update your config via `mdl --setup`.

**"Spotify API credentials not found"**
- Ensure you have correctly set the `client_id` and `client_secret` in your `mdl-config.toml`.

## License

MIT
