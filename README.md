# Music Downloader

A command-line tool to download Spotify playlists and tracks using Streamrip, preferring Deezer with Qobuz as a backup.

## Installation

```bash
# Install using pipx (recommended)
pipx install .

# Alternatively, install with pip
pip install .
```

## Usage

```bash
# Download a Spotify track
music-downloader "https://open.spotify.com/track/your-track-id"

# Download a Spotify playlist
music-downloader "https://open.spotify.com/playlist/your-playlist-id"
```

## Configuration

Spotify API credentials can be stored in:
1. `~/.config/music-downloader/.env` (highest priority)
2. `~/.env`
3. `./.env` (in current working directory)

Format of `.env` file:
```
SPOTIPY_CLIENT_ID=your-spotify-client-id
SPOTIPY_CLIENT_SECRET=your-spotify-client-secret
```

## Output

Files are downloaded to the `./Output` directory, relative to where the command is run.
An M3U playlist file is created in the same directory.
