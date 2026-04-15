# Music Downloader

Download tracks from Deezer using search queries or Spotify links. Built on [streamrip](https://github.com/nathom/streamrip).

## Quick Start

1. **Install pipx** (if you don't have it):
   ```bash
   brew install pipx
   ```

2. **Clone and install**:
   ```bash
   git clone https://github.com/justinjohnso/music-downloader.git
   cd music-downloader
   pipx install .
   ```

3. **Run the setup wizard** — it'll walk you through everything (Deezer login, download folder, quality):
   ```bash
   mdl --setup
   ```

   The generated `mdl-config.toml` lives in the platform app-support location only:
   - macOS: `~/Library/Application Support/music-downloader/mdl-config.toml`
   - Linux: `~/.config/music-downloader/mdl-config.toml`
   - Windows: `~/AppData/Roaming/music-downloader/mdl-config.toml`

You're good to go.

## Usage

```bash
# Search for a track (interactive candidate selection by default in TTY)
mdl "TroyBoi - Dale"

# Download a Spotify track
mdl "https://open.spotify.com/track/0aym2LBJBk9DAYuHHutrIl"

# Download an entire Spotify playlist (generates an M3U file too)
mdl "https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF"

# Force first-result behavior (non-interactive)
mdl --first-result "TroyBoi - Dale"

# Adjust interactive candidate list size
mdl --result-limit 15 "TroyBoi - Dale"
```

### Interactive matching behavior

- **CLI (default in TTY):** shows Deezer candidates and prompts you to pick the intended match.
- **CLI `--first-result`:** skips prompts and downloads the first Deezer match.
- **CLI Spotify playlists:** supported; in interactive mode you can select matches per track.

## Spotify Credentials

To download Spotify links, you must provide your own Spotify credentials in `mdl-config.toml`:

```toml
[spotify]
client_id = "your-client-id"
client_secret = "your-client-secret"
```

Get them from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).

## Deezer ARL

To download from Deezer, you need an ARL cookie from your Deezer account. The setup wizard will ask for it and explain where to find it.

ARLs expire every 3-4 months. When yours stops working, grab a fresh one and run `mdl --setup` again. Instructions for finding your ARL: [streamrip wiki](https://github.com/nathom/streamrip/wiki/Finding-Your-Deezer-ARL-Cookie).

## Troubleshooting

**"mdl: command not found"**
- pipx might not be in your PATH. Try: `pipx ensurepath`, then restart your terminal.
- Verify it installed: `pipx list | grep music-downloader`

**"ARL expired" or "Login failed"**
- Your Deezer ARL has probably expired. Get a new one from the [wiki](https://github.com/nathom/streamrip/wiki/Finding-Your-Deezer-ARL-Cookie), then run `mdl --setup` to update it.

**Downloads failing or tracks not found**
- Run with `--verbose` to see what's happening: `mdl --verbose "Artist - Track"`
- Try interactive matching (default) to pick a better Deezer result instead of relying on first match.

## License

MIT
