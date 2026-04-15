# AGENTS.md

## Build, Test & Run Commands

- **Install globally with pipx**: `pipx install .` (creates `mdl` and `music-downloader` commands system-wide)
- **Reinstall after changes**: `pipx install --force .`
- **Run CLI** (after installation):
  - `mdl <query_or_spotify_link> [--verbose]`
  - `python -m src.downloader <query_or_spotify_link> [--verbose]` (direct, no install needed)
- **Tests**: None currently. Add pytest tests in `tests/` if adding features. pytest + pytest-asyncio are already in requirements.txt.
- **Lint/Format**: `black src/` (not currently enforced but preferred)

## Architecture

```
src/
  downloader.py   # CLI entry point (argparse). Delegates to core.
  core.py         # Download logic: download_track, download_multiple_tracks, process_spotify_link
  spotify.py      # Spotify API: get_spotify_tracks, is_spotify_link, extract_spotify_info
  config.py       # Config loading: load_config, apply_config_overrides, ensure_streamrip_config_exists
```

**Data flow**: User input (query or Spotify link) -> `downloader.py` dispatches -> `core.py` handles download via streamrip's `DeezerClient` -> results saved to configured download folder.

**Key dependencies**:
- `streamrip` -- Deezer/Qobuz download engine. Uses its internal `Config`, `DeezerClient`, `PendingTrack`, `AlbumMetadata` types. Config is loaded from platform-specific paths and overridden by mdl-config.toml.
- `spotipy` -- Spotify Web API client for extracting track metadata from links/URIs
- `tomlkit` -- TOML parsing (preserves formatting and comments)
- `appdirs` -- Platform-specific directory paths

**Configuration**: `mdl-config.toml` (gitignored, copy from `mdl-config-example.toml`). Overrides all streamrip config values. Key sections: `[spotify]` (credentials), `[deezer]` (ARL cookie, quality), `[qobuz]`, `[tidal]`, `[downloads]` (folder, concurrency), `[artwork]`, `[filepaths]`, `[conversions]`.

Config search order (in `config.py`): cwd -> home dir -> platform config dir (`~/Library/Application Support/music-downloader/` on macOS).

## Patterns & Gotchas

**Async**: All download functions are async. `download_track` and `download_multiple_tracks` each create their own `DeezerClient`, login, and clean up the aiohttp session in `try...finally`.

**Session cleanup**: The aiohttp session cleanup in `core.py` is verbose and fragile -- it cancels all pending tasks, closes the session, closes the connector, then sleeps 0.1s. This pattern is duplicated between `download_track` and `download_multiple_tracks`. A shared context manager would reduce duplication.

**streamrip dual config**: streamrip has both `config.session` (runtime) and `config.file` (TOML-backed). After overriding `config.session`, `apply_config_overrides` must also sync values to `config.file` (see end of `config.py`). Missing syncs cause silent failures where downloads use default paths.

**M3U generation**: Only generates for playlists, only lists `.mp3` files (misses `.flac`/`.m4a`). The M3U lists all mp3 files in the download folder, not just the ones from the current playlist.

**Import style**: `core.py` and `spotify.py` use deferred imports (`from src.config import ...` inside functions) to avoid circular imports.

## Code Style

- Python 3.10+ (system Python via `.python-version`)
- PEP 8, type hints on all function signatures
- Google-style docstrings on public functions
- `snake_case` for functions/variables, `UPPER_CASE` for constants
- Standard lib imports first, then third-party, then local

## Engineering Mandates

- **Commit Style**: 
  - ALWAYS use multiple surgical commits for distinct changes (e.g., separate core logic, UI overhaul, and documentation).
  - NEVER use generic prefixes like `feat:`, `fix:`, or `chore:`.
  - Focus commit messages on the "why" of the change rather than the "what".
  - Propose a commit plan before executing batch commits.

---

*Last updated: April 2026*
