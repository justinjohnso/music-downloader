# Music Downloader Agent Instructions

You are Gemini CLI, assisting with the `music-downloader` project. This file serves as the shared context for all AI agents (Gemini, Claude, Cursor) working on this codebase.

## Project Mission
A robust Python-based tool for downloading high-quality music tracks from Deezer (with Qobuz fallback) using search queries or Spotify links. The tool aims to be simple, fast, and highly configurable.

## Tech Stack
- Language: Python 3.10+
- UI: PyQt6 (GUI)
- Core Engine: streamrip (Vendored in vendor/streamrip)
- APIs: spotipy (Spotify metadata), deezer-py
- Config: tomlkit
- Tooling: ruff (linting/formatting), pytest (testing)

## Project Structure
- src/downloader.py: CLI entry point (mdl).
- src/gui.py: PyQt6 GUI implementation (mdl-gui).
- src/core.py: Main download logic (wraps streamrip functionality).
- src/spotify.py: Spotify link parsing and metadata extraction.
- src/config.py: Global config management, streamrip monkey-patching, and setup wizard.
- vendor/streamrip: Submodule containing the core engine. Do not modify directly unless patching behavior.

## Configuration and Global Behavior
- Config Path: mdl searches in CWD, User Home, and Platform App Support.
- Submodule Pathing: src/__init__.py injects vendor/streamrip into sys.path.
- Safe Mode: Logic in src/config.py prevents overwriting user-customized streamrip configs.
- Monkey-patching: Use src/config.py to patch streamrip behavior (e.g., config versioning) at runtime.

## Executable Commands
| Action | Command |
| :--- | :--- |
| Run CLI | python3 -m src.downloader or mdl |
| Run GUI | python3 -m src.downloader --gui or mdl-gui |
| Setup Wizard | mdl --setup |
| Lint Check | ruff check . |
| Format Code | ruff format . |
| Install | pipx install . |

## Code Style and Conventions
- Naming: PEP 8 (snake_case for variables/functions, PascalCase for classes).
- Formatting: Use ruff format (Black compatible).
- Typing: Use type hints for all function signatures and complex variables.
- Documentation: Google-style docstrings for all public methods and classes.
- Linting: Address all ruff findings before finishing. No noqa unless absolutely necessary.

## Boundaries and Security
- Never Touch: .git/, __pycache__/, build/, dist/.
- Submodule Changes: Be careful when updating vendor/streamrip. Prefer monkey-patching in src/config.py over direct edits to the submodule.
- Secrets: Never log or commit ARLs, tokens, or credentials. Use mdl-config.toml (ignored by git).
- Git: NEVER push changes to a remote or run `git commit` without an explicit instruction from the user. Default to staging changes only and suggesting a commit message when appropriate.

## Verification Checklist
Before declaring a task "done," ensure:
1. All changes follow the defined Code Style.
2. ruff check . and ruff format . have been executed.
3. Behavior has been verified via the CLI or GUI.
