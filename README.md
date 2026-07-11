# Music Downloader

A Python CLI and GUI tool that extends [streamrip](https://github.com/nathom/streamrip) for downloading high-quality music tracks from Deezer (with Qobuz fallback) based on search queries or Spotify links.

## Quick Start

1. **Install pipx and Python 3** (if you don't have them):
   - **macOS**:
     ```bash
     brew install pipx python
     brew install jpeg-turbo pkgconf
     ```
   - **Windows**:
     Install [Python 3.10+](https://www.python.org/downloads/).
     You will also need the [Microsoft Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) to compile C-extensions like `cffi`.
     Then install pipx:
     ```cmd
     py -m pip install --user pipx
     py -m pipx ensurepath
     ```

1. **Clone and install**:
   ```bash
   git clone --recursive https://github.com/justinjohnso/music-downloader.git
   cd music-downloader
   pipx install .
   ```

1. **Create Spotify Dev App** (if you're not using default creds):
   
   This is where you'll get your client ID & secret for the MDL setup. Use `http://127.0.0.1:8888/callback` as the redirect URI.
   - Info: https://developer.spotify.com/documentation/web-api/concepts/apps
   - Link: https://developer.spotify.com/

1. **Run the setup wizard** — it will walk you through Deezer login, download folder, and quality settings:
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

# Download an entire Spotify playlist or album
mdl "https://open.spotify.com/playlist/..."
mdl "https://open.spotify.com/album/..."

# Run with detailed output
mdl --verbose "Artist - Track"

# Sync downloads DB from your configured downloads/library folder
mdl --sync-db

# Sync downloads DB from a specific folder
mdl --sync-db "/path/to/library/folder"

# Quickly update an expired Deezer ARL without re-running full setup
mdl --set-arl
mdl --set-arl "YOUR_NEW_ARL_HERE"
```

### GUI
Launch the graphical interface for a user-friendly experience:
```bash
mdl-gui
```

## Configuration

### Config location

`mdl-config.toml` is stored at the platform-appropriate application support directory:

| Platform | Path |
|----------|------|
| macOS    | `~/Library/Application Support/music-downloader/mdl-config.toml` |
| Linux    | `~/.config/music-downloader/mdl-config.toml` |
| Windows  | `~/AppData/Roaming/music-downloader/mdl-config.toml` |

Legacy paths (`~/mdl-config.toml`, `./mdl-config.toml`) are still detected and a one-time migration prompt is shown. Run `mdl --setup` to move to the modern location.

The file contains full streamrip configuration (all 15 sections) plus a `[spotify]` section. It is written with `chmod 600` on POSIX systems — keep it private as it holds your Deezer ARL.

### Setup wizard

Run `mdl --setup` to interactively configure:
1. **Deezer ARL** (required) — validated on entry
2. **Download folder**
3. **Audio quality** — 320kbps MP3 or FLAC
4. **Spotify credentials** (optional) — for resolving Spotify links
5. **Advanced options** (optional, press Enter to skip each):
   - Download concurrency and max connections
   - Qobuz and Tidal credentials
   - Audio conversion codec
   - Filepath folder format

Re-running setup is safe — it preserves any values you have manually edited in the file, only updating the keys you explicitly answer.

### Auto-repair

On every `mdl` invocation, the tool silently checks that your config contains all required sections and keys. If anything is missing (e.g., after a streamrip schema update), it is filled in from defaults and logged at INFO level. No action required.

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
- Your Deezer ARL has likely expired. Get a new one from the browser and update your config quickly via `mdl --set-arl` or re-run the full wizard via `mdl --setup`.

**"Spotify API credentials not found"**
- Ensure you have correctly set the `client_id` and `client_secret` in your `mdl-config.toml` from your Spotify Developer Application (https://developer.spotify.com/).

## Regenerating the Example Config

`mdl-config-example.toml` is generated from the current setup wizard defaults. To update it after schema changes:

```bash
python scripts/regen-example-config.py
```

## Maintaining Vendored streamrip Overrides

This project keeps `vendor/streamrip` as a submodule and stores local vendor edits as patch files so updates stay manageable.

Use:

```bash
# Export current local streamrip edits to a patch file
./scripts/streamrip-overrides.sh export

# Inspect patch/submodule state
./scripts/streamrip-overrides.sh status

# Check if patch applies cleanly to current submodule checkout
./scripts/streamrip-overrides.sh check

# Apply patch to a clean submodule working tree
./scripts/streamrip-overrides.sh apply
```

Patch location:

```text
vendor/streamrip-patches/0001-local-overrides.patch
```

Recommended update flow:
1. Update submodule to desired upstream revision.
2. Run `./scripts/streamrip-overrides.sh check`.
3. If clean, run `./scripts/streamrip-overrides.sh apply`.
4. Re-run project verification (`ruff check .` and tests).

## License

MIT
