# 2025-04-26: Adding pipx Support

I decided to make the script installable as a global command-line tool using `pipx`. This would make it much more convenient to use, since I could run it from anywhere without needing to remember where the script is or manually activate the virtual environment each time.

First, I needed to create a `pyproject.toml` file to define the package structure. This file tells Python's packaging tools what to install and how:

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "music-downloader"
version = "0.1.0"
description = "Downloads songs from Spotify playlists using Streamrip"
readme = "README.md"
requires-python = ">=3.8"
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
dependencies = [
    "streamrip",
    "spotipy",
    "python-dotenv",
    "appdirs",
]

[project.scripts]
music-downloader = "downloader:main"
```

The most important part is the `[project.scripts]` section, which creates a command named `music-downloader` that calls the `main()` function in the `downloader.py` module.

I made sure the script's configuration and environment handling was robust enough to work when called from any location. The key changes were:

1. Using `appdirs.user_config_dir()` to find a standard config directory that works across operating systems.
2. Setting up logging to go to `~/.config/music-downloader/downloader.log` so logs are centralized.
3. Supporting `.env` files in multiple locations with a priority order:
   - `~/.config/music-downloader/.env` (highest priority)
   - `~/.env`
   - `./.env` (current directory where command is run)

Added a simple README.md file with installation and usage instructions.

Now I can install the tool with:
```bash
pipx install .
```

And then run it from anywhere:
```bash
music-downloader "https://open.spotify.com/playlist/my-playlist-id"
```

Much easier than having to find the script and activate a virtual environment every time!
