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
