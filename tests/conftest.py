"""Shared fixtures for the mdl test suite."""
import os
import sys
import pytest
from pathlib import Path


@pytest.fixture()
def tmp_config_dir(tmp_path, monkeypatch):
    """Redirect all config/data dirs to *tmp_path* before any streamrip import.

    Sets HOME and XDG_CONFIG_HOME env vars so that streamrip's APP_DIR
    (computed at import time) is also redirected when the module is first
    imported within this test process.
    """
    config_dir = tmp_path / "config" / "music-downloader"
    data_dir = tmp_path / "data" / "streamrip"
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Patch env vars before any streamrip import
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    # Patch the helper functions in src.config
    import src.config as sc
    monkeypatch.setattr(sc, "_get_mdl_config_dir", lambda: config_dir)
    monkeypatch.setattr(sc, "_get_streamrip_data_dir", lambda: data_dir)

    yield {
        "config_dir": config_dir,
        "data_dir": data_dir,
        "config_path": config_dir / "mdl-config.toml",
        "tmp_path": tmp_path,
    }
