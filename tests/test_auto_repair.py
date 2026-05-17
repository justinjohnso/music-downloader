"""Tests for ensure_mdl_config_complete (auto-repair on startup)."""
import logging
import tomlkit
import pytest
from pathlib import Path

from src.config import ensure_mdl_config_complete, _secure_write


def _write_minimal(path: Path, extra: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "[deezer]\narl = \"MY_ARL\"\nquality = 1\n"
    if extra:
        content += extra
    _secure_write(path, content)


def test_missing_database_section_is_filled(tmp_config_dir):
    path = tmp_config_dir["config_path"]
    _write_minimal(path)

    ensure_mdl_config_complete()

    doc = tomlkit.parse(path.read_text())
    assert "database" in doc
    assert doc["database"]["downloads_path"], "downloads_path should be non-empty"
    # ARL preserved
    assert doc["deezer"]["arl"] == "MY_ARL"


def test_legacy_conversions_renamed(tmp_config_dir):
    path = tmp_config_dir["config_path"]
    content = (
        "[deezer]\narl = \"MY_ARL\"\nquality = 1\n\n"
        "[conversions]\nenabled = false\ncodec = \"ALAC\"\n"
    )
    _secure_write(path, content)

    ensure_mdl_config_complete()

    doc = tomlkit.parse(path.read_text())
    assert "conversion" in doc, "Should be renamed to singular"
    assert "conversions" not in doc, "Plural form should be gone"
    assert doc["conversion"]["codec"] == "ALAC"


def test_empty_database_path_filled(tmp_config_dir):
    path = tmp_config_dir["config_path"]
    content = (
        "[deezer]\narl = \"MY_ARL\"\nquality = 1\n\n"
        "[database]\ndownloads_enabled = true\ndownloads_path = \"\"\n"
        "failed_downloads_enabled = true\nfailed_downloads_path = \"\"\n"
    )
    _secure_write(path, content)

    ensure_mdl_config_complete()

    doc = tomlkit.parse(path.read_text())
    assert doc["database"]["downloads_path"], "Should be filled"
    assert doc["database"]["failed_downloads_path"], "Should be filled"


def test_db_parent_dir_created(tmp_config_dir):
    path = tmp_config_dir["config_path"]
    data_dir = tmp_config_dir["data_dir"]
    _write_minimal(path)

    ensure_mdl_config_complete()

    doc = tomlkit.parse(path.read_text())
    db_path = Path(doc["database"]["downloads_path"])
    assert db_path.parent.exists(), "Parent dir for db path should be created"


def test_auto_repair_expands_tilde_in_database_paths(tmp_config_dir):
    path = tmp_config_dir["config_path"]
    content = (
        "[deezer]\narl = \"MY_ARL\"\nquality = 1\n\n"
        "[database]\ndownloads_enabled = true\n"
        "downloads_path = \"~/Library/Application Support/streamrip/downloads.db\"\n"
        "failed_downloads_enabled = true\n"
        "failed_downloads_path = \"~/Library/Application Support/streamrip/failed.db\"\n"
    )
    _secure_write(path, content)

    ensure_mdl_config_complete()

    doc = tomlkit.parse(path.read_text())
    dl_path = doc["database"]["downloads_path"]
    fd_path = doc["database"]["failed_downloads_path"]
    assert "~" not in dl_path, "downloads_path should not contain ~"
    assert "~" not in fd_path, "failed_downloads_path should not contain ~"
    assert dl_path.startswith("/"), "downloads_path should be absolute"
    assert fd_path.startswith("/"), "failed_downloads_path should be absolute"
    assert doc["deezer"]["arl"] == "MY_ARL", "arl should be preserved"


def test_no_op_when_config_complete(tmp_config_dir, caplog):
    from src.config import _write_or_update_config

    path = tmp_config_dir["config_path"]
    prompted = {
        "arl": "MY_ARL",
        "quality": 1,
        "folder": "/tmp/music",
        "spotify_id": "",
        "spotify_secret": "",
    }
    _write_or_update_config(path, prompted)

    before = path.read_bytes()

    with caplog.at_level(logging.INFO, logger="mdl"):
        ensure_mdl_config_complete()

    after = path.read_bytes()
    assert before == after
    assert "filled in missing" not in caplog.text
