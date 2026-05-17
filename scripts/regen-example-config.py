#!/usr/bin/env python
"""Regenerate mdl-config-example.toml from the current _build_config_toml output.

Usage:
    python scripts/regen-example-config.py
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path so src imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import _build_config_toml  # noqa: E402

OUTPUT = Path(__file__).resolve().parents[1] / "mdl-config-example.toml"

import os

folder_display = "~/Music/Music Downloader"
content = _build_config_toml(
    arl="PASTE_YOUR_ARL_HERE",
    quality=1,
    folder=folder_display,
    spotify_id="",
    spotify_secret="",
)
# The generator expands the home dir; restore the tilde form for the example file
content = content.replace(
    f'"{os.path.expanduser(folder_display)}"',
    f'"{folder_display}"',
    1,
)

OUTPUT.write_text(content, encoding="utf-8")
print(f"Written: {OUTPUT}")
