# Music Downloader

Python CLI and PyQt6 GUI for downloading from Deezer using search queries or Spotify track, playlist, and album links. Spotify supplies metadata; audio comes from Deezer through bundled [streamrip](https://github.com/nathom/streamrip).

Downloads use the first Deezer match by default. The development checkout adds `mdl --search "Artist - Track"` to list matches and `--select` to choose one; these are not in published `0.1.0`. Qobuz fallback and a hosted Spotify backend are not provided.

## Installation

Requires Python 3.10 or later and pipx. FFmpeg is required only when audio conversion is enabled.

On macOS:

```bash
brew install pipx python
pipx ensurepath
```

On Windows, install Python and pipx:

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
```

Some pinned dependencies require compilation when a wheel is unavailable. Windows builds can require Visual C++ Build Tools.

Clone with the streamrip submodule and install:

```bash
git clone --recursive https://github.com/justinjohnso/music-downloader.git
cd music-downloader
pipx install .
mdl --setup
```

PyQt6 is installed with the application. Linux GUI users also need Qt system libraries, including `libegl1` and `libopengl0` on Debian/Ubuntu. Desktop requirements depend on the platform plugin; see [Qt Linux requirements](https://doc.qt.io/qt-6/linux-requirements.html). CLI commands do not import Qt.

## Usage

```bash
mdl "The Beatles - Hey Jude"
mdl "https://open.spotify.com/track/TRACK_ID"
mdl "https://open.spotify.com/playlist/PLAYLIST_ID"
mdl "spotify:album:ALBUM_ID"
mdl --verbose "Artist - Track"
mdl-gui
```

Use Spotify IDs in place of the uppercase placeholders. URLs can include query parameters. Track, playlist, and album URIs are supported.

Downloads require a valid Deezer ARL. FLAC also requires suitable account access and available source files. With quality fallback enabled, an unavailable FLAC file can fall back to MP3.

Spotify track and album lookup uses app credentials. Playlist lookup first tries app credentials, then user OAuth for access-related failures. A private playlist must be accessible to the authenticated user. OAuth uses `http://127.0.0.1:8888/callback` and stores tokens at `~/.cache-music-downloader-spotify`.

The application includes fallback Spotify app credentials, but their continued availability is not guaranteed. Configure your own app through the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and register that redirect URI.

See the [complete command reference](docs/cli.md) for every flag, command precedence, and duplicate handling.

## Configuration

Run `mdl --setup` for the ARL, download folder, quality, optional Spotify credentials, and selected advanced settings.

| Platform | Primary mdl config |
| --- | --- |
| macOS | `~/Library/Application Support/music-downloader/mdl-config.toml` |
| Linux | `~/.config/music-downloader/mdl-config.toml` (or under `XDG_CONFIG_HOME`) |
| Windows | `%APPDATA%/music-downloader/mdl-config.toml` |

CLI lookup checks the primary path, then `~/mdl-config.toml`, then `./mdl-config.toml`. Setup offers migration for a legacy file. Declining migration keeps that location.

Setup writes all 15 streamrip sections plus `[spotify]`. Many sections are inherited for compatibility but are not used by mdl. The [complete config reference](docs/configuration.md) lists every key, default, and runtime limitation. Prefer editing TOML directly for list-valued or advanced settings.

```toml
[deezer]
arl = "YOUR_ARL"
quality = 1
lower_quality_if_not_available = true

[spotify]
client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"
```

This is a configuration fragment, not a complete file. Run setup first. `quality = 1` selects 320kbps MP3; `2` requests FLAC.

### Preservation and credentials

Setup retains existing mdl values and uses them as prompt defaults. Migration preserves custom keys and comments. Independently customized streamrip config files remain unchanged during setup and download overrides; mdl uses its own session settings.

Refresh an ARL with the masked prompt:

```bash
mdl --set-arl
```

Refresh validates the credential before writing and changes only `deezer.arl` in both files. It does not repair the schema or copy other settings. ARLs can expire or be revoked; no fixed lifetime is guaranteed.

CLI config writes use private temporary files and atomic replacement. On POSIX, these files have mode `600`. If the second ARL write fails, mdl attempts to restore the first file. A crash between writes can leave different credentials.

The development GUI groups search results by artist/album and supports a sequential queue with retries, rematching, cancellation, and distinct downloaded/skipped/failed outcomes. Choose an engine config, import batch queries, or export JSON results from the interface. CLI batch/retry/JSON commands and GUI queues use the same workflow.
The config editor masks credentials, preserves arrays/comments, and saves only changed fields against the latest file using private atomic writes. A native setup dialog validates ARL before saving; CLI setup remains available for advanced options. These GUI improvements are not in published `0.1.0`.

### Auto-repair

Download commands, database sync, and bare `mdl` repair missing schema keys after finding a config. Setup runs repair after saving. Help, GUI entrypoints, and ARL refresh do not perform this repair.

Repair fills missing keys, renames legacy `[conversions]` when `[conversion]` is absent, and expands tilde-prefixed database paths without changing their destination. It does not validate all values or replace missing credentials. Missing download folders can remain empty; run setup to select a destination.

## Download history and library sync

Download history stores Deezer track IDs. Single-track duplicates can prompt for skip or redownload. Batch downloads initially skip duplicates, then offer review in an interactive terminal. Noninteractive runs skip duplicate review.

```bash
mdl --sync-db
mdl --sync-db "/path/to/library"
```

Sync recursively reads lowercase `.mp3`, `.flac`, `.m4a`, and `.ogg` files. It resolves their tags on Deezer and adds matching IDs to the configured database. It requires title/artist tags and Deezer login. It does not change audio files or download tracks.

## Known limits

- Matching by artist/title can select a different recording or version. Tracks are processed sequentially.
- Playlist metadata retains the matched Deezer album and track number; inherited playlist-tag options are inactive.
- Current M3U output lists sorted `.mp3` files directly in the destination, including unrelated files. It excludes FLAC and nested folders, and does not preserve Spotify order.
- Conversion deletes the original after success. The inherited `lossy_bitrate` option is not passed to the converter.
- Some download failures are printed without a failing process exit code. Check output and resulting files when automating.

## Updating

For an installation made from this checkout:

```bash
git pull --ff-only
git submodule update --init --recursive
pipx reinstall music-downloader
mdl --help
```

If Git reports divergent history, stop and preserve local work before integration. Do not rerun setup merely to update the application. Updating does not require changing the library or credential config.

## Development

Use an isolated environment with the project dependencies and Ruff installed:

```bash
python -m pytest -ra
ruff check .
ruff format --check .
```

CI builds a wheel, checks dependencies, and runs tests and installed CLI/GUI smoke on Linux, macOS, and Windows with Python 3.10 and 3.14. Ruff excludes vendored code. GUI smoke uses a temporary config without authentication or downloads.

Regenerate the example config with:

```bash
python scripts/regen-example-config.py
```

The generator uses the current platform's database paths. Review those paths before sharing the example. The example also retains upstream comments; consult the config reference for mdl-specific behavior.

`vendor/streamrip` is pinned as a Git submodule. Existing patch helpers are documented in `vendor/streamrip-patches/README.md`. Do not apply a historical patch blindly to an already patched revision. Keep vendor changes separate and verify the schema and application tests.

Historical implementation notes live in `docs/ai/`; they are not user documentation or current release status.

## Troubleshooting

- **Command not found:** run `pipx ensurepath`, then open a new terminal. Check for conflicting installations on your PATH.
- **Deezer login failed:** obtain a valid ARL and run `mdl --set-arl`. Credential-free download fallback is not supported.
- **Spotify access failure:** verify your app credentials, registered redirect URI, app/user access, and playlist permissions. Public access does not prove private-playlist access.
- **Missing vendored config:** initialize the submodule with `git submodule update --init --recursive`, then reinstall.
- **Conversion failed:** check FFmpeg availability and codec support. AAC requires the `libfdk_aac` encoder.

## License

The wrapper is MIT licensed. Bundled streamrip is GPL-3.0-only, and both license texts are included in distributions. Redistribution of the combined package must comply with the applicable GPL terms. This is not a blanket MIT grant for the vendored code.
