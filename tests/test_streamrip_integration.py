"""Integration test: config produced by mdl can be loaded by streamrip."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import tomlkit

from src.config import (
    _write_or_update_config,
    merge_mdl_config_into_streamrip,
)


def test_streamrip_config_constructs_without_error(tmp_config_dir, tmp_path):
    """After setup pipeline, streamrip.config.Config loads cleanly."""
    from streamrip.config import Config

    mdl_path = tmp_config_dir["config_path"]
    prompted = {
        "arl": "TESTARL",
        "quality": 1,
        "folder": str(tmp_path / "music"),
        "spotify_id": "",
        "spotify_secret": "",
    }
    _write_or_update_config(mdl_path, prompted)

    # Build a streamrip config in a temp location
    sr_config_path = tmp_path / "streamrip" / "config.toml"
    sr_config_path.parent.mkdir(parents=True, exist_ok=True)
    from streamrip.config import set_user_defaults

    set_user_defaults(str(sr_config_path))

    merge_mdl_config_into_streamrip(
        str(sr_config_path),
        tomlkit.parse(mdl_path.read_text()),
    )

    # This should not raise
    config = Config(str(sr_config_path))
    assert config.session.deezer.arl == "TESTARL"


def test_apply_config_overrides_maps_deezer_quality(tmp_path):
    """apply_config_overrides must correctly map mdl quality to streamrip quality."""
    from streamrip.config import Config, set_user_defaults
    from src.config import apply_config_overrides

    sr_config_path = tmp_path / "streamrip" / "config.toml"
    sr_config_path.parent.mkdir(parents=True, exist_ok=True)
    set_user_defaults(str(sr_config_path))

    config = Config(str(sr_config_path))

    # Test mapping 1 -> 1
    apply_config_overrides(config, {"deezer": {"quality": 1}})
    assert config.session.deezer.quality == 1

    # Test mapping 2 -> 2
    apply_config_overrides(config, {"deezer": {"quality": 2}})
    assert config.session.deezer.quality == 2

    # Test fallback to 1
    apply_config_overrides(config, {"deezer": {"quality": 999}})
    assert config.session.deezer.quality == 1


def test_apply_config_overrides_expands_tilde(tmp_path):
    """apply_config_overrides must expand ~ in database path values."""
    from streamrip.config import Config, set_user_defaults
    from src.config import apply_config_overrides

    sr_config_path = tmp_path / "streamrip" / "config.toml"
    sr_config_path.parent.mkdir(parents=True, exist_ok=True)
    set_user_defaults(str(sr_config_path))

    config = Config(str(sr_config_path))

    config_data = {
        "database": {
            "downloads_path": "~/Library/Application Support/streamrip/downloads.db",
            "failed_downloads_path": "~/Library/Application Support/streamrip/failed.db",
        }
    }

    apply_config_overrides(config, config_data)

    assert "~" not in config.session.database.downloads_path
    assert "~" not in config.session.database.failed_downloads_path
    assert Path(config.session.database.downloads_path).is_absolute()
    assert Path(config.session.database.failed_downloads_path).is_absolute()


@pytest.mark.parametrize(
    ("requested", "sizes", "expected"),
    [
        (1, [100, 200, 300], 1),
        (2, [100, 200, 300], 2),
        (2, [100, 200, 0], 1),
        (1, [100, 0, 0], 0),
    ],
    ids=["mp3-320", "flac", "flac-to-mp3", "mp3-to-128"],
)
def test_deezer_fallback_matches_selected_quality(requested, sizes, expected):
    from Cryptodome.Cipher import AES
    from streamrip.client.deezer import DeezerClient

    client = object.__new__(DeezerClient)
    client.config = SimpleNamespace(lower_quality_if_not_available=True)
    client.session = None
    client.client = MagicMock()
    client.client.gw.get_track.return_value = {
        "FILESIZE_MP3_128": sizes[0],
        "FILESIZE_MP3_320": sizes[1],
        "FILESIZE_FLAC": sizes[2],
        "TRACK_TOKEN": "test-token",
        "MD5_ORIGIN": "0123456789abcdef0123456789abcdef",
        "MEDIA_VERSION": "1",
    }
    client.client.get_track_url.return_value = None
    downloadable = asyncio.run(client.get_downloadable("123", requested))
    assert downloadable.quality == expected
    assert downloadable.extension == ("flac" if expected == 2 else "mp3")
    path = downloadable.url.rsplit("/", 1)[1]
    decoded = AES.new(b"jo6aey6haid2Teih", AES.MODE_ECB).decrypt(bytes.fromhex(path))
    assert decoded.split(b"\xa4")[2] == str([9, 3, 1][expected]).encode()


def test_deezer_unavailable_quality_does_not_fallback_when_disabled():
    from streamrip.client.deezer import DeezerClient
    from streamrip.exceptions import NonStreamableError

    client = object.__new__(DeezerClient)
    client.config = SimpleNamespace(lower_quality_if_not_available=False)
    client.client = MagicMock()
    client.client.gw.get_track.return_value = {
        "FILESIZE_MP3_128": 100,
        "FILESIZE_MP3_320": 200,
        "FILESIZE_FLAC": 0,
    }
    with pytest.raises(NonStreamableError, match="fallback is disabled"):
        asyncio.run(client.get_downloadable("123", 2))
    client.client.get_track_url.assert_not_called()
