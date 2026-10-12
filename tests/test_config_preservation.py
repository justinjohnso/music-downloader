from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import tomlkit

import src.config as config


@pytest.fixture()
def config_files(tmp_config_dir, monkeypatch):
    from streamrip.config import set_user_defaults

    mdl = tmp_config_dir["config_path"]
    sr = tmp_config_dir["data_dir"] / "config.toml"
    set_user_defaults(str(sr))
    config._secure_write(
        mdl,
        '# user note\n[deezer]\narl = "OLD"\nquality = 1\n'
        '[downloads]\nfolder = "~/custom-music"\n[custom]\nvalue = "keep"\n',
    )
    doc = tomlkit.parse(sr.read_text())
    doc["downloads"]["folder"] = str(tmp_config_dir["tmp_path"] / "independent")
    doc["database"]["downloads_path"] = str(
        tmp_config_dir["tmp_path"] / "independent.db"
    )
    doc["deezer"]["arl"] = "SR_OLD"
    doc["conversion"]["codec"] = "OGG"
    config._secure_write(sr, "# streamrip note\n" + tomlkit.dumps(doc))
    monkeypatch.setattr(config, "get_default_config_path", lambda: str(sr))
    monkeypatch.setattr(config, "_validate_deezer_arl", lambda *args, **kwargs: True)
    return mdl, sr


def test_set_arl_changes_only_credentials_in_both_files(config_files):
    mdl, sr = config_files
    expected_mdl = mdl.read_text().replace('arl = "OLD"', 'arl = "NEW"')
    expected_sr = sr.read_text().replace('arl = "SR_OLD"', 'arl = "NEW"')
    config.set_arl("NEW")
    assert mdl.read_text() == expected_mdl
    assert sr.read_text() == expected_sr


def test_set_arl_rejects_malformed_streamrip_before_writing_mdl(config_files):
    mdl, sr = config_files
    before = mdl.read_bytes()
    sr.write_text("invalid = [")
    with pytest.raises(Exception):
        config.set_arl("NEW")
    assert mdl.read_bytes() == before
    assert sr.read_text() == "invalid = ["


def test_set_arl_recovers_mdl_when_second_write_fails(config_files, monkeypatch):
    mdl, sr = config_files
    before = mdl.read_bytes(), sr.read_bytes()
    original_write = config._secure_write

    def fail_streamrip(path, content):
        if Path(path) == sr:
            raise OSError("write denied")
        original_write(path, content)

    monkeypatch.setattr(config, "_secure_write", fail_streamrip)
    with pytest.raises(OSError, match="write denied"):
        config.set_arl("NEW")
    assert (mdl.read_bytes(), sr.read_bytes()) == before


def test_merge_preserves_custom_streamrip_bytes(config_files):
    _, sr = config_files
    before = sr.read_bytes()
    config.merge_mdl_config_into_streamrip(
        str(sr), {"downloads": {"folder": "other"}, "deezer": {"arl": "NEW"}}
    )
    assert sr.read_bytes() == before


def test_path_only_customization_is_detected(tmp_path, monkeypatch):
    from streamrip.config import set_user_defaults

    sr = tmp_path / "config.toml"
    set_user_defaults(str(sr))
    doc = tomlkit.parse(sr.read_text())
    doc["database"]["downloads_path"] = str(tmp_path / "custom.db")
    sr.write_text(tomlkit.dumps(doc))
    monkeypatch.setattr(config, "get_default_config_path", lambda: str(sr))
    assert config.is_streamrip_config_customized()


def test_session_overrides_check_actual_target(config_files, tmp_path, monkeypatch):
    from streamrip.config import Config, set_user_defaults

    _, sr = config_files
    default = tmp_path / "default.toml"
    set_user_defaults(str(default))
    monkeypatch.setattr(config, "get_default_config_path", lambda: str(default))
    actual = Config(str(sr))
    actual.file.deezer.quality = 1
    before = sr.read_bytes()
    config.apply_config_overrides(actual, {"deezer": {"quality": 2}})
    assert actual.session.deezer.quality == 2
    assert actual.file.deezer.quality == 1
    assert sr.read_bytes() == before


def test_validation_does_not_create_streamrip_file(tmp_path, monkeypatch):
    sr = tmp_path / "missing.toml"
    monkeypatch.setattr(config, "get_default_config_path", lambda: str(sr))

    class RejectLogin:
        def __init__(self, settings):
            self.session = None

        async def login(self):
            raise ValueError("rejected")

    monkeypatch.setattr("streamrip.client.DeezerClient", RejectLogin)
    assert config._validate_deezer_arl("BAD") is False
    assert not sr.exists()


def test_secure_write_temp_is_private_before_replace(tmp_path, monkeypatch):
    path = tmp_path / "config.toml"
    seen = []
    original_replace = os.replace

    def inspect_replace(source, destination):
        if os.name == "posix":
            assert stat.S_IMODE(Path(source).stat().st_mode) == 0o600
        seen.append(Path(source))
        original_replace(source, destination)

    monkeypatch.setattr(config.os, "replace", inspect_replace)
    config._secure_write(path, "secret")
    assert seen and path.read_text() == "secret"
    assert not seen[0].exists()


def test_secure_write_failure_leaves_original_and_no_temp(tmp_path, monkeypatch):
    path = tmp_path / "config.toml"
    path.write_text("original")
    monkeypatch.setattr(config.os, "replace", MagicMock(side_effect=OSError("denied")))
    with pytest.raises(OSError):
        config._secure_write(path, "new")
    assert path.read_text() == "original"
    assert list(tmp_path.iterdir()) == [path]


def test_auto_repair_expands_custom_database_path_without_relocation(tmp_config_dir):
    mdl = tmp_config_dir["config_path"]
    mdl.write_text(
        '[deezer]\narl = "OLD"\n[database]\ndownloads_path = "~/custom/history.db"\n'
    )
    config.ensure_mdl_config_complete()
    doc = tomlkit.parse(mdl.read_text())
    assert doc["database"]["downloads_path"] == os.path.expanduser(
        "~/custom/history.db"
    )


def test_setup_fills_paths_in_added_database_section(config_files):
    mdl, _ = config_files
    config._write_or_update_config(
        mdl, {"arl": "NEW", "quality": 1, "folder": "~/custom-music"}
    )
    doc = tomlkit.parse(mdl.read_text())
    assert doc["database"]["downloads_path"]
    assert doc["database"]["failed_downloads_path"]


@pytest.mark.parametrize("migrate", [True, False])
def test_setup_preserves_legacy_values_and_respects_migration(
    config_files, tmp_config_dir, monkeypatch, migrate
):
    mdl, sr = config_files
    legacy = tmp_config_dir["tmp_path"] / "legacy.toml"
    mdl.rename(legacy)
    monkeypatch.setattr(
        config,
        "load_config_with_path",
        lambda **kwargs: (tomlkit.parse(legacy.read_text()), str(legacy)),
    )
    answers = iter([migrate, False, False, False])
    monkeypatch.setattr(
        "rich.prompt.Confirm.ask", lambda *args, **kwargs: next(answers)
    )
    monkeypatch.setattr(
        "rich.prompt.Prompt.ask", lambda *args, **kwargs: str(kwargs.get("default", ""))
    )
    before_sr = sr.read_bytes()
    config.run_setup_wizard()
    target = mdl if migrate else legacy
    assert target.exists()
    assert tomlkit.parse(target.read_text())["custom"]["value"] == "keep"
    assert "# user note" in target.read_text()
    if not migrate:
        assert not mdl.exists()
    assert sr.read_bytes() == before_sr


def test_setup_advanced_defaults_preserve_current_values(config_files, monkeypatch):
    mdl, _ = config_files
    config._write_or_update_config(
        mdl,
        {"arl": "OLD", "quality": 1, "folder": "~/custom-music"},
        advanced={
            "downloads": {"concurrency": False, "max_connections": 9},
            "conversion": {"enabled": True, "codec": "FLAC"},
            "filepaths": {"folder_format": "CUSTOM"},
        },
    )
    answers = iter([False, True])
    monkeypatch.setattr(
        "rich.prompt.Confirm.ask", lambda *args, **kwargs: next(answers)
    )
    monkeypatch.setattr(
        "rich.prompt.Prompt.ask", lambda *args, **kwargs: str(kwargs.get("default", ""))
    )
    config.run_setup_wizard()
    doc = tomlkit.parse(mdl.read_text())
    assert doc["downloads"]["concurrency"] is False
    assert doc["downloads"]["max_connections"] == 9
    assert doc["conversion"]["enabled"] is True
    assert doc["conversion"]["codec"] == "FLAC"
    assert doc["filepaths"]["folder_format"] == "CUSTOM"


def test_streamrip_creation_is_secure_and_failure_does_not_leave_empty_file(
    tmp_path, monkeypatch
):
    sr = tmp_path / "new" / "config.toml"
    monkeypatch.setattr(config, "get_default_config_path", lambda: str(sr))
    config.ensure_streamrip_config_exists()
    if os.name == "posix":
        assert stat.S_IMODE(sr.stat().st_mode) == 0o600
    sr.unlink()
    monkeypatch.setattr(
        config, "_secure_write", MagicMock(side_effect=OSError("denied"))
    )
    with pytest.raises(OSError):
        config.ensure_streamrip_config_exists()
    assert not sr.exists()


def test_default_streamrip_merge_still_applies_setup_values(tmp_path):
    from streamrip.config import set_user_defaults

    sr = tmp_path / "default.toml"
    set_user_defaults(str(sr))
    config.merge_mdl_config_into_streamrip(
        str(sr), {"deezer": {"arl": "NEW", "quality": 1}}
    )
    doc = tomlkit.parse(sr.read_text())
    assert doc["deezer"]["arl"] == "NEW"
    assert doc["deezer"]["quality"] == 1
    if os.name == "posix":
        assert stat.S_IMODE(sr.stat().st_mode) == 0o600


def test_set_arl_preserves_crlf_bytes(config_files):
    mdl, sr = config_files
    for path in (mdl, sr):
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    expected = tuple(
        path.read_bytes()
        .replace(b'arl = "OLD"', b'arl = "NEW"')
        .replace(b'arl = "SR_OLD"', b'arl = "NEW"')
        for path in (mdl, sr)
    )
    config.set_arl("NEW")
    assert tuple(path.read_bytes() for path in (mdl, sr)) == expected


def test_streamrip_loader_reads_utf8_independent_of_locale(tmp_path, monkeypatch):
    import builtins
    from streamrip.config import Config, set_user_defaults

    sr = tmp_path / "config.toml"
    set_user_defaults(str(sr))
    doc = tomlkit.parse(sr.read_text())
    doc["downloads"]["folder"] = "音楽"
    sr.write_text(tomlkit.dumps(doc), encoding="utf-8")
    original_open = builtins.open

    def locale_open(path, *args, **kwargs):
        if Path(path) == sr and "encoding" not in kwargs:
            kwargs["encoding"] = "cp1252"
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", locale_open)
    assert Config(str(sr)).file.downloads.folder == "音楽"


def test_default_session_overrides_are_persisted_securely(tmp_path):
    from streamrip.config import Config, set_user_defaults

    sr = tmp_path / "config.toml"
    set_user_defaults(str(sr))
    config.apply_config_overrides(Config(str(sr)), {"deezer": {"quality": 1}})
    assert tomlkit.parse(sr.read_text())["deezer"]["quality"] == 1
    if os.name == "posix":
        assert stat.S_IMODE(sr.stat().st_mode) == 0o600


def test_set_arl_missing_streamrip_uses_user_defaults(config_files):
    from streamrip.config import Config

    _, sr = config_files
    sr.unlink()
    config.set_arl("NEW")
    actual = Config(str(sr))
    assert actual.file.deezer.arl == "NEW"
    assert actual.file.downloads.folder
    assert actual.file.youtube.video_downloads_folder


def test_setup_preserves_legacy_conversion_values(config_files):
    mdl, _ = config_files
    with mdl.open("a") as stream:
        stream.write('[conversions]\nenabled = true\ncodec = "FLAC"\n')
    config._write_or_update_config(
        mdl, {"arl": "OLD", "quality": 1, "folder": "~/custom-music"}
    )
    doc = tomlkit.parse(mdl.read_text())
    assert "conversions" not in doc
    assert doc["conversion"]["enabled"] is True
    assert doc["conversion"]["codec"] == "FLAC"


def test_failed_migration_does_not_publish_preferred_config(
    config_files, tmp_config_dir, monkeypatch
):
    mdl, _ = config_files
    legacy = tmp_config_dir["tmp_path"] / "legacy.toml"
    mdl.rename(legacy)
    original = legacy.read_bytes()
    monkeypatch.setattr(
        config,
        "load_config_with_path",
        lambda **kwargs: (tomlkit.parse(legacy.read_text()), str(legacy)),
    )
    answers = iter([True, False, False])
    monkeypatch.setattr(
        "rich.prompt.Confirm.ask", lambda *args, **kwargs: next(answers)
    )
    monkeypatch.setattr(
        "rich.prompt.Prompt.ask", lambda *args, **kwargs: str(kwargs.get("default", ""))
    )
    monkeypatch.setattr(
        config, "_write_or_update_config", MagicMock(side_effect=OSError("denied"))
    )
    config.run_setup_wizard()
    assert not mdl.exists()
    assert legacy.read_bytes() == original
