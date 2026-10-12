import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from src.core import download_track_with_client


def test_download_uses_session_folder_and_artwork(tmp_path, monkeypatch):
    import src.core as core

    client = MagicMock(source="deezer", session=MagicMock())
    client.search = AsyncMock(
        return_value=[
            {
                "id": "123",
                "title": "Track",
                "artist": {"name": "Artist"},
                "album": {"id": "456"},
            }
        ]
    )
    client.get_metadata = AsyncMock(return_value={})
    artwork = SimpleNamespace()
    settings = SimpleNamespace(
        session=SimpleNamespace(
            downloads=SimpleNamespace(folder=str(tmp_path / "mdl")), artwork=artwork
        ),
        file=SimpleNamespace(
            downloads=SimpleNamespace(folder=str(tmp_path / "standalone")),
            artwork=SimpleNamespace(),
        ),
    )
    db = MagicMock()
    db.downloaded.return_value = False
    monkeypatch.setattr(
        core.AlbumMetadata, "from_album_resp", lambda *args: SimpleNamespace(covers=[])
    )
    cover = AsyncMock(return_value=(None, None))
    monkeypatch.setattr(core, "download_artwork", cover)
    pending = MagicMock()
    pending.return_value.resolve = AsyncMock(
        return_value=SimpleNamespace(rip=AsyncMock())
    )
    monkeypatch.setattr(core, "PendingTrack", pending)
    status, _ = asyncio.run(
        download_track_with_client(client, settings, "Artist Track", db=db)
    )
    assert status == "downloaded"
    assert pending.call_args.kwargs["folder"] == settings.session.downloads.folder
    assert cover.call_args.args[3] is artwork
    assert not (tmp_path / "standalone").exists()


def test_selected_duplicate_uses_original_id_and_does_not_search(tmp_path, monkeypatch):
    from src.search import build_track_candidate

    candidate = build_track_candidate(
        {
            "id": "123",
            "title": "Chosen",
            "artist": {"name": "Artist"},
            "album": {"id": "456"},
        }
    )
    client = MagicMock()
    db = MagicMock()
    db.downloaded.return_value = True
    status, label = asyncio.run(
        download_track_with_client(
            client,
            SimpleNamespace(),
            "query",
            db=db,
            duplicate_mode="skip",
            selected_candidate=candidate,
        )
    )
    assert status == "duplicate_skipped"
    assert label == "Chosen by Artist"
    client.search.assert_not_called()
    db.downloaded.assert_called_once_with("123")
