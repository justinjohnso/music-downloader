from src.playlists import write_playlist


def test_playlist_uses_actual_paths_formats_and_source_order(tmp_path):
    unrelated = tmp_path / "unrelated.mp3"
    unrelated.write_bytes(b"audio")
    nested = tmp_path / "Disc 2" / "z.flac"
    nested.parent.mkdir()
    nested.write_bytes(b"audio")
    converted = tmp_path / "a.m4a"
    converted.write_bytes(b"audio")
    playlist = write_playlist(
        tmp_path, "Test / Playlist", [nested, converted, tmp_path / "missing.mp3"]
    )
    assert playlist.read_text().splitlines() == ["Disc 2/z.flac", "a.m4a"]
    assert "unrelated" not in playlist.read_text()


def test_no_playlist_when_nothing_downloaded(tmp_path):
    assert write_playlist(tmp_path, "Empty", []) is None
    assert not list(tmp_path.iterdir())


def test_unsafe_playlist_name_has_safe_fallback(tmp_path):
    audio = tmp_path / "song.mp3"
    audio.write_bytes(b"audio")
    playlist = write_playlist(tmp_path, "../", [audio])
    assert playlist.name == "Playlist.m3u"


def test_batch_keeps_duplicate_redownload_in_original_position(tmp_path, monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock
    import src.core as core

    settings = SimpleNamespace(
        session=SimpleNamespace(
            downloads=SimpleNamespace(folder=str(tmp_path)), update_toml=lambda: None
        )
    )
    client = SimpleNamespace(login=AsyncMock())
    monkeypatch.setattr(core, "Config", lambda *_: settings)
    monkeypatch.setattr(core, "DeezerClient", lambda *_: client)
    monkeypatch.setattr(core, "_build_database_from_config", lambda *_: MagicMock())
    monkeypatch.setattr("src.config.load_config_with_path", lambda **kwargs: ({}, None))
    monkeypatch.setattr("src.config.apply_config_overrides", lambda *_: None)
    monkeypatch.setattr(core, "_offer_duplicate_review", lambda items: items)

    async def immediate_sleep(*args):
        return None

    monkeypatch.setattr(core.asyncio, "sleep", immediate_sleep)

    async def download(
        client, config, query, db, verbose, duplicate_mode, downloaded_path_callback
    ):
        if "First" in query and duplicate_mode == "skip":
            return "duplicate_skipped", "First"
        path = tmp_path / ("first.flac" if "First" in query else "second.mp3")
        path.write_bytes(b"audio")
        downloaded_path_callback(str(path))
        return "downloaded", query

    monkeypatch.setattr(core, "download_track_with_client", download)
    asyncio.run(
        core.download_multiple_tracks(
            [
                {"artist": "Artist", "title": "First"},
                {"artist": "Artist", "title": "Second"},
            ],
            config_path="unused",
            is_playlist=True,
            playlist_name="Order",
        )
    )
    assert (tmp_path / "Order.m3u").read_text().splitlines() == [
        "first.flac",
        "second.mp3",
    ]
