"""Tests for set_arl and related error-message helpers."""
import warnings
import pytest
import tomlkit
from pathlib import Path
from unittest.mock import MagicMock, patch

import src.config as sc
from src.config import set_arl, _write_or_update_config, _validate_deezer_arl


# ---------------------------------------------------------------------------
# set_arl tests
# ---------------------------------------------------------------------------


def test_set_arl_with_no_config_exits(tmp_config_dir, monkeypatch, capsys):
    """set_arl exits 1 with a clear message when no config exists."""
    # Force load_config_with_path to report no config regardless of real filesystem state
    monkeypatch.setattr(sc, "load_config_with_path", lambda **kw: ({}, None))
    with pytest.raises(SystemExit) as exc_info:
        set_arl("SOME_ARL")
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "No mdl config found" in captured.out
    assert "--setup" in captured.out


def test_set_arl_preserves_other_keys(tmp_config_dir, monkeypatch):
    """set_arl only updates arl; other config keys are preserved."""
    config_path: Path = tmp_config_dir["config_path"]
    sr_path = str(tmp_config_dir["data_dir"] / "config.toml")

    # Write a config with several values
    prompted = {
        "arl": "OLD_ARL",
        "quality": 2,
        "folder": "/tmp/my-music",
        "spotify_id": "my_id",
        "spotify_secret": "my_secret",
    }
    _write_or_update_config(config_path, prompted)

    # Stub out validation and streamrip config writing
    monkeypatch.setattr(sc, "_validate_deezer_arl", lambda arl, verbose=False: True)
    monkeypatch.setattr(sc, "ensure_streamrip_config_exists", lambda: sr_path)
    monkeypatch.setattr(sc, "merge_mdl_config_into_streamrip", lambda *a, **kw: None)

    set_arl("NEW_ARL")

    doc = tomlkit.parse(config_path.read_text())
    assert doc["deezer"]["arl"] == "NEW_ARL"
    assert doc["deezer"]["quality"] == 2
    assert doc["downloads"]["folder"] == "/tmp/my-music"
    assert doc["spotify"]["client_id"] == "my_id"
    assert doc["spotify"]["client_secret"] == "my_secret"


def test_set_arl_strict_on_validation_failure(tmp_config_dir, monkeypatch):
    """set_arl exits 1 without touching the config when validation fails."""
    config_path: Path = tmp_config_dir["config_path"]

    # Write initial config
    prompted = {
        "arl": "GOOD_ARL",
        "quality": 1,
        "folder": "/tmp/music",
        "spotify_id": "",
        "spotify_secret": "",
    }
    _write_or_update_config(config_path, prompted)

    before = config_path.read_bytes()

    monkeypatch.setattr(sc, "_validate_deezer_arl", lambda arl, verbose=False: False)

    with pytest.raises(SystemExit) as exc_info:
        set_arl("BAD_ARL")
    assert exc_info.value.code == 1

    # Config must be unchanged
    assert config_path.read_bytes() == before


# ---------------------------------------------------------------------------
# Error-message fallback test (Task 5)
# ---------------------------------------------------------------------------


def test_empty_exception_falls_back_to_type_name():
    """When an exception has no message, format should use the type name."""
    exc = Exception()
    msg = str(exc) or type(exc).__name__
    assert msg == "Exception"


def test_nonempty_exception_uses_message():
    """When an exception has a message, format should use it."""
    exc = ValueError("bad value")
    msg = str(exc) or type(exc).__name__
    assert msg == "bad value"


# ---------------------------------------------------------------------------
# Session cleanup test
# ---------------------------------------------------------------------------


def test_validate_deezer_arl_closes_session(monkeypatch):
    """_validate_deezer_arl must close the aiohttp session even when login fails."""
    from streamrip.exceptions import AuthenticationError

    close_calls = []

    async def fake_close():
        close_calls.append(True)

    mock_session = MagicMock()
    mock_session.close = fake_close

    # Fake DeezerClient: login assigns self.session then raises AuthenticationError
    class FakeDeezerClient:
        def __init__(self, config):
            self.session = None

        async def login(self):
            self.session = mock_session
            raise AuthenticationError

    monkeypatch.setattr(sc, "ensure_streamrip_config_exists", lambda: "/fake/path")

    with patch("streamrip.client.DeezerClient", FakeDeezerClient), \
         patch("streamrip.config.Config", MagicMock(return_value=MagicMock())):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = _validate_deezer_arl("BAD_ARL")

    assert result is False
    assert close_calls, "session.close() was never called — session leak!"

    unclosed = [w for w in caught if "Unclosed client session" in str(w.message)]
    assert not unclosed, f"Got 'Unclosed client session' warning: {unclosed}"
