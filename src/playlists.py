from __future__ import annotations

import os
from pathlib import Path

from .config import _secure_write


def write_playlist(
    folder: str | Path, name: str, paths: list[str | Path]
) -> Path | None:
    """Write only actual downloaded files in the supplied source order."""
    root = Path(folder)
    entries = [Path(path) for path in paths if Path(path).is_file()]
    if not entries:
        return None
    safe_name = (
        "".join(
            character for character in name if character.isalnum() or character in " -_"
        ).strip()
        or "Playlist"
    )
    safe_name = safe_name.encode("utf-8")[:180].decode("utf-8", errors="ignore")
    playlist = root / f"{safe_name}.m3u"
    lines = [Path(os.path.relpath(path, root)).as_posix() for path in entries]
    lines = ["./" + line if line.startswith("#") else line for line in lines]
    if any("\n" in line or "\r" in line for line in lines):
        raise ValueError("Playlist file paths cannot contain line breaks")
    _secure_write(playlist, "".join(line + "\n" for line in lines))
    return playlist
