# 2025-04-26: Initial Setup and Core Script Implementation

Okay, starting fresh on the music downloader script.

**Goal:** Create a Python script to take a Spotify track/playlist URL, download the songs using Streamrip (preferring Deezer, falling back to Qobuz), save them to an `Output` folder, and generate an M3U playlist.

**Setup Steps:**

1.  **Environment:**
    *   Used `pyenv local system` to stick with the system Python for this project.
    *   Created a virtual environment: `python -m venv .venv`.
    *   Installed necessary packages: `pip install streamrip spotipy python-dotenv`. Streamrip's scripting API looks like the way to go, rather than trying to call the `/usr/local/bin/rip` executable directly from Python.
    *   Generated `requirements.txt` using `pip freeze`.
    *   Added `.venv`, `.env`, `__pycache__`, `*.pyc`, and `downloader.log` to `.gitignore`. Also added `Output/` for now, assuming downloaded music shouldn't be committed.

2.  **Credentials:**
    *   Created a `.env` file and stored the provided Spotify `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET`. This keeps them out of the code.

3.  **Documentation:**
    *   Set up the `Documentation/` folder.
    *   Created `Documentation/code-references.md` and added links to Streamrip, Spotipy, and the Python modules I anticipate using (`dotenv`, `argparse`, `pathlib`, `logging`).
    *   Started this log file (`Documentation/Posts/2025-04-26-initial-setup-and-script.md`).
    *   Created `.github/copilot-references.md` for tracking code sources.

**Next:** Implement the core Python script (`downloader.py`). This will involve:
    *   Parsing arguments.
    *   Loading the `.env` file.
    *   Setting up Spotipy.
    *   Fetching track details from Spotify.
    *   Calling the Streamrip API (`streamrip.api.rip`) for downloads with the Deezer/Qobuz fallback logic.
    *   Handling the results from Streamrip to get the downloaded file paths.
    *   Generating the M3U playlist file.
