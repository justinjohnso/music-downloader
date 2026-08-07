# Music Downloader

A lightweight, robust CLI and GUI application for downloading high-quality music directly from Deezer (with Qobuz fallback). Built on top of streamrip, it supports searching for tracks or passing Spotify links to seamlessly match and download your music.

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Built with](https://img.shields.io/badge/built%20with-streamrip-purple)

<!-- screenshot_placeholder: gui_or_cli_hero.png -->

## Features

- **Spotify Integration:** Paste a Spotify track or playlist link to download the matching tracks.
- **Direct Search:** Search for artists, albums, or tracks directly from the command line.
- **High Quality Audio:** Choose between 320kbps MP3 or lossless FLAC.
- **Automatic M3U Generation:** Creates `.m3u` playlists for downloaded albums and Spotify playlists.
- **Interactive Setup:** First-run wizard makes configuring credentials and folders a breeze.
- **Dual Interfaces:** Features a clean GUI (`mdl-gui`) alongside the powerful CLI (`mdl`).
- **Self-Healing Config:** Safely manages configurations and synchronizes them with the streamrip engine.

## Quick Start

**1. Install Dependencies**
Ensure you have `pipx` and Python 3.10+ installed.

**2. Clone & Install**
```bash
git clone --recursive https://github.com/justinjohnso/music-downloader.git
cd music-downloader
pipx install .
```

**3. Run Setup Wizard**
The interactive setup will configure your Deezer cookie, download folder, and quality preferences.
```bash
mdl --setup
```

## Usage Examples

You can use the CLI or launch the graphical interface.

**CLI**
```bash
# Search and download a specific track
mdl "The Beatles - Hey Jude"

# Download a track using a Spotify link
mdl "https://open.spotify.com/track/..."

# Download an entire Spotify playlist
mdl "https://open.spotify.com/playlist/..."

# Quick ARL update if your Deezer login expires
mdl --set-arl
```

**GUI**
Launch the graphical interface for an easy-to-use search and download experience:
```bash
mdl-gui
```
<!-- screenshot_placeholder: gui_app_window.png -->

## Configuration

The application is configured via `mdl-config.toml`, located in your platform's standard application support directory:
- **macOS:** `~/Library/Application Support/music-downloader/mdl-config.toml`
- **Linux:** `~/.config/music-downloader/mdl-config.toml`
- **Windows:** `~/AppData/Roaming/music-downloader/mdl-config.toml`

For most users, running `mdl --setup` will handle all necessary configuration. Advanced users can manually edit this file to override streamrip's engine settings.

## Deezer ARL

To download from Deezer, you must provide an ARL (cookie) from a logged-in account. The setup wizard will prompt you for this.
- **How to find it:** See the [streamrip wiki](https://github.com/nathom/streamrip/wiki/Finding-Your-Deezer-ARL-Cookie).
- **Expiry:** Deezer ARLs expire every 3-4 months. When downloads fail due to authentication, grab a fresh ARL and run `mdl --set-arl`.

## Spotify Integration

Spotify links are resolved into `Artist - Title` queries and searched on Deezer. The CLI uses pre-configured local Spotify Developer credentials by default.

*(Optional)* **Self-Hosted Spotify Backend:** If you prefer running a centralized resolver to keep Spotify credentials completely off the client device, a FastAPI backend implementation is available in the `backend/` directory.

## Project Structure

- `src/` — Core CLI, GUI, configuration management, and Spotify resolver
- `tests/` — Pytest suite covering configuration and auto-repair logic
- `vendor/streamrip/` — Git submodule containing the core streamrip engine
- `backend/` — (Optional) FastAPI-based Spotify resolver backend

## Troubleshooting

- **"mdl: command not found"**
  Ensure `pipx` is in your PATH. Run `pipx ensurepath` and restart your terminal.
- **"Deezer login failed" or "Your Deezer ARL has expired"**
  Your ARL has likely expired. Grab a new one and run `mdl --set-arl`.
- **Streamrip Vendor Errors**
  If you see vendor missing errors during installation, ensure you cloned the repo with `--recursive` or run `git submodule update --init --recursive`.

## Contributing

Pull requests are welcome! Before submitting, ensure that your code is formatted with `ruff format .` and passes the test suite (`pytest -ra`).

## License & Credits

This project is licensed under the [MIT License](LICENSE).

Heavily built upon [streamrip](https://github.com/nathom/streamrip). Massive thanks to its contributors for the core engine!
