"""Tests that guard against schema drift between streamrip and mdl."""
import os
import tomlkit
import pytest
from pathlib import Path

from src.schema import iter_section_keys, STREAMRIP_SECTIONS
from src.config import _build_config_toml


# Keys handled by _apply_to_session (manually kept in sync with the function)
KNOWN_KEYS: dict[str, set[str]] = {
    "deezer": {
        "arl",
        "quality",
        "lower_quality_if_not_available",
        "use_deezloader",
        "deezloader_warnings",
    },
    "qobuz": {
        "email_or_userid",
        "password_or_token",
        "use_auth_token",
        "app_id",
        "quality",
        "download_booklets",
        "secrets",
    },
    "tidal": {
        "user_id",
        "country_code",
        "access_token",
        "refresh_token",
        "token_expiry",
        "quality",
        "download_videos",
    },
    "soundcloud": {"client_id", "app_version", "quality"},
    "youtube": {"video_downloads_folder", "quality", "download_videos"},
    "downloads": {
        "folder",
        "source_subdirectories",
        "disc_subdirectories",
        "concurrency",
        "max_connections",
        "requests_per_minute",
        "verify_ssl",
    },
    "artwork": {
        "embed",
        "embed_size",
        "embed_max_width",
        "save_artwork",
        "saved_max_width",
    },
    "metadata": {"set_playlist_to_album", "renumber_playlist_tracks", "exclude"},
    "filepaths": {
        "add_singles_to_folder",
        "folder_format",
        "track_format",
        "restrict_characters",
        "truncate_to",
    },
    "conversion": {"enabled", "codec", "sampling_rate", "bit_depth", "lossy_bitrate"},
    "qobuz_filters": {
        "extras",
        "repeats",
        "non_albums",
        "features",
        "non_studio_albums",
        "non_remaster",
    },
    "database": {
        "downloads_enabled",
        "downloads_path",
        "failed_downloads_enabled",
        "failed_downloads_path",
    },
    "lastfm": {"source", "fallback_source"},
    "cli": {"text_output", "progress_bars", "max_search_results"},
    "misc": {"version", "check_for_updates"},
}


def test_all_streamrip_keys_are_known():
    """Every key in the vendored schema is recognised in KNOWN_KEYS."""
    unknown = []
    for section, key in iter_section_keys():
        if section not in KNOWN_KEYS or key not in KNOWN_KEYS[section]:
            unknown.append(f"{section}.{key}")
    assert not unknown, (
        "New keys in vendored streamrip schema not yet handled in _apply_to_session:\n"
        + "\n".join(unknown)
    )


_SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "default_mdl_config.toml"
_UPDATE_SNAPSHOTS = os.getenv("UPDATE_SNAPSHOTS") == "1"


def test_snapshot_default_config(monkeypatch):
    """_build_config_toml output matches the checked-in snapshot.

    Uses a stable fake data dir so the db paths in the output are reproducible.
    """
    import src.config as sc

    fake_data = Path("/tmp/streamrip-snapshot-data")
    monkeypatch.setattr(sc, "_get_streamrip_data_dir", lambda: fake_data)

    actual = _build_config_toml(
        "PASTE_YOUR_ARL_HERE", 1, "/tmp/music-downloader-snapshot", "", ""
    )

    if _UPDATE_SNAPSHOTS:
        _SNAPSHOT_PATH.write_text(actual, encoding="utf-8")
        pytest.skip("Snapshot updated")

    expected = _SNAPSHOT_PATH.read_text(encoding="utf-8")
    assert actual == expected, (
        "Snapshot mismatch. Re-run with UPDATE_SNAPSHOTS=1 to refresh."
    )
