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

# Launch the GUI
mdl --gui

# Force first-result behavior (non-interactive)
mdl --first-result "TroyBoi - Dale"

# Adjust interactive candidate list size
mdl --result-limit 15 "TroyBoi - Dale"
```

### Interactive matching behavior

- **CLI (default in TTY):** shows Deezer candidates and prompts you to pick the intended match.
- **CLI `--first-result`:** skips prompts and downloads the first Deezer match.
- **CLI Spotify playlists:** supported; in interactive mode you can select matches per track.
- **GUI query + Spotify track links:** search first, then select and download one Deezer candidate.
- **GUI Spotify playlists:** supported with an explicit confirmation for first-result matching.

## Spotify Resolution (Backend-First)

Spotify links are resolved in this order:

1. `[backend] resolve_url` + `api_key` in `mdl-config.toml` (recommended)
2. Optional local `[spotify] client_id` + `client_secret` fallback

Behavior:
- If backend is configured and reachable, the app uses backend results.
- If backend request fails and local Spotify credentials are present, the app falls back to local Spotipy resolution.
- If neither backend nor local credentials are configured, Spotify link downloads fail with setup guidance.

Example `mdl-config.toml`:

```toml
[backend]
resolve_url = "https://your-domain.example.com/spotify/resolve"
api_key = "replace-with-shared-api-key"

[spotify]
# Optional fallback only:
# client_id = "..."
# client_secret = "..."
```

## Backend Service Setup

The backend lives in `backend/` and exposes `POST /spotify/resolve`.

```bash
cd backend
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Required backend runtime environment variables:

- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_BACKEND_API_KEY` (must match client-side `[backend].api_key`)

See `backend/README.md` for endpoint and deployment details.

## GitHub Secrets (Deploy + Runtime)

For the DigitalOcean VPS deploy model in this repo brief, configure these as GitHub Actions secrets:

### Deployment access secrets
- `DO_VPS_HOST`
- `DO_VPS_USER`
- `DO_VPS_SSH_PRIVATE_KEY`
- `DO_VPS_SSH_PORT` (optional if non-default)

### Backend runtime secrets
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_BACKEND_API_KEY`

Deployment assumption: GitHub Actions deploys to an always-on DigitalOcean VPS, and runtime secrets are injected on-host (or via environment file) without committing values to git.

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
