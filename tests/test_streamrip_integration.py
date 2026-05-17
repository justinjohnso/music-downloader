"""Integration test: config produced by mdl can be loaded by streamrip."""
import tomlkit
import pytest
from pathlib import Path

from src.config import (
    _build_config_toml,
    _write_or_update_config,
    merge_mdl_config_into_streamrip,
    ensure_streamrip_config_exists,
    get_default_config_path,
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
    assert config.session.database.downloads_path.startswith("/")
    assert config.session.database.failed_downloads_path.startswith("/")
