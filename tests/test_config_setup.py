"""Tests for the setup wizard config writer."""
import os
import stat
import tomlkit
import pytest

from src.schema import STREAMRIP_SECTIONS
from src.config import _build_config_toml, _write_or_update_config


def test_empty_system_setup_writes_all_sections(tmp_config_dir):
    path = tmp_config_dir["config_path"]
    prompted = {
        "arl": "TESTARL",
        "quality": 1,
        "folder": "/tmp/music",
        "spotify_id": "",
        "spotify_secret": "",
    }
    _write_or_update_config(path, prompted)

    assert path.exists()
    doc = tomlkit.parse(path.read_text())
    sections = set(doc.keys())

    missing = STREAMRIP_SECTIONS - sections
    assert not missing, f"Missing streamrip sections: {missing}"
    assert "spotify" in sections


def test_rerun_preserves_user_concurrency(tmp_config_dir):
    path = tmp_config_dir["config_path"]
    prompted = {
        "arl": "TESTARL",
        "quality": 1,
        "folder": "/tmp/music",
        "spotify_id": "",
        "spotify_secret": "",
    }
    _write_or_update_config(path, prompted)

    # User manually edits concurrency
    doc = tomlkit.parse(path.read_text())
    doc["downloads"]["concurrency"] = False
    path.write_text(tomlkit.dumps(doc))

    # Re-run setup
    _write_or_update_config(path, prompted)

    doc2 = tomlkit.parse(path.read_text())
    assert doc2["downloads"]["concurrency"] is False


def test_banner_present(tmp_config_dir):
    content = _build_config_toml("ARL", 1, "/tmp/x", "", "")
    assert content.startswith("# mdl — music-downloader config")
    assert "Do not share" in content
    assert "mdl --setup" in content


@pytest.mark.skipif(os.name != "posix", reason="POSIX only")
def test_file_permissions_600(tmp_config_dir):
    path = tmp_config_dir["config_path"]
    prompted = {
        "arl": "TESTARL",
        "quality": 1,
        "folder": "/tmp/music",
        "spotify_id": "",
        "spotify_secret": "",
    }
    _write_or_update_config(path, prompted)

    file_mode = stat.S_IMODE(os.stat(path).st_mode)
    assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"
