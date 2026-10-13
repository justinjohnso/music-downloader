import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src import streamrip_search


@pytest.fixture()
def adapter(monkeypatch):
    config = MagicMock()
    client = SimpleNamespace(
        search=AsyncMock(
            return_value=[
                {"data": [{"id": 7, "title": "Track", "artist": {"name": "Artist"}}]}
            ]
        ),
        session=SimpleNamespace(closed=False, close=AsyncMock()),
        logged_in=True,
    )
    engine = SimpleNamespace(
        get_logged_in_client=AsyncMock(return_value=client),
        search_interactive=AsyncMock(),
        add_by_id=AsyncMock(),
        pending=[],
        database=MagicMock(),
    )
    client.search_mock = client.search
    engine.database.downloaded.return_value = False
    monkeypatch.setattr(streamrip_search, "_search_config", lambda *_: config)
    monkeypatch.setattr("streamrip.client.DeezerClient", lambda *_: client)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    return config, client, engine


def test_escape_selection_does_not_resolve_or_download(adapter):
    config, client, engine = adapter
    assert (
        asyncio.run(
            streamrip_search.run_search("query", engine_factory=lambda *_: engine)
        )
        == 0
    )
    engine.search_interactive.assert_awaited_once_with("deezer", "track", "query")
    engine.add_by_id.assert_not_called()
    client.session.close.assert_awaited_once()
    config.save_file.assert_not_called()


def test_export_does_not_download_or_open_terminal(adapter, tmp_path):
    _, client, engine = adapter
    destination = tmp_path / "results.json"
    assert (
        asyncio.run(
            streamrip_search.run_search(
                "query",
                output_file=str(destination),
                num_results=2,
                engine_factory=lambda *_: engine,
            )
        )
        == 0
    )
    assert json.loads(destination.read_text())[0]["id"] == "7"
    engine.search_interactive.assert_not_called()
    engine.add_by_id.assert_not_called()
    assert client.search_mock.call_args.kwargs["limit"] == 2


def test_first_result_adds_correct_id(adapter):
    _, client, engine = adapter
    assert (
        asyncio.run(
            streamrip_search.run_search(
                "query", first=True, engine_factory=lambda *_: engine
            )
        )
        == 0
    )
    engine.add_by_id.assert_awaited_once_with("deezer", "track", "7")
    engine.search_interactive.assert_not_called()


def test_resolution_failure_is_not_success(adapter):
    _, client, engine = adapter
    pending = SimpleNamespace(id="7", resolve=AsyncMock(return_value=None))
    engine.pending.append(pending)
    assert (
        asyncio.run(
            streamrip_search.run_search("query", engine_factory=lambda *_: engine)
        )
        == 1
    )
    client.session.close.assert_awaited_once()


def test_export_refuses_to_replace_existing_file(tmp_path):
    destination = tmp_path / "config.toml"
    destination.write_text("preserve")
    with pytest.raises(ValueError, match="already exists"):
        asyncio.run(streamrip_search.run_search("query", output_file=str(destination)))
    assert destination.read_text() == "preserve"


def test_no_terminal_requires_explicit_noninteractive_mode(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(RuntimeError, match="requires a terminal"):
        asyncio.run(streamrip_search.run_search("query"))


def test_config_loading_does_not_write_standalone_file(tmp_path, monkeypatch):
    from streamrip.config import set_user_defaults

    path = tmp_path / "config.toml"
    set_user_defaults(str(path))
    before = path.read_bytes()
    monkeypatch.setattr(
        streamrip_search,
        "load_config",
        lambda: {
            "deezer": {"arl": "TEST", "quality": 1},
            "downloads": {"folder": str(tmp_path)},
        },
    )
    config = streamrip_search._search_config(str(path))
    assert config.session.deezer.arl == "TEST"
    assert config.file.deezer.arl != "TEST"
    assert path.read_bytes() == before


def test_artist_shapes_and_empty_pages():
    pages = [
        {
            "data": [
                {"id": 1, "title": "A", "artist": "Artist"},
                {"id": 2, "title": "B", "artists": [{"name": "Other"}]},
                {"name": "invalid"},
            ]
        }
    ]
    results = streamrip_search._normalized_pages(pages, 2)[0]["data"]
    assert [item["artist"]["name"] for item in results] == ["Artist", "Other"]
    assert streamrip_search._normalized_pages([{"data": []}], 10) == []


def test_real_upstream_menu_escape_is_non_destructive(tmp_path, monkeypatch):
    from streamrip.client import DeezerClient
    from streamrip.config import Config
    from simple_term_menu import TerminalMenu

    config = Config.defaults()
    config.session.deezer.arl = "TEST"
    config.session.downloads.folder = str(tmp_path)
    config.session.database.downloads_path = str(tmp_path / "history.db")
    config.session.database.failed_downloads_path = str(tmp_path / "failed.db")
    monkeypatch.setattr(streamrip_search, "_search_config", lambda *_: config)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr("platform.system", lambda: "Linux")

    async def login(self):
        self.logged_in = True

    monkeypatch.setattr(DeezerClient, "login", login)
    search = AsyncMock(
        return_value=[
            {"data": [{"id": 7, "title": "Glitter", "artist": {"name": "Jkyl & Hyde"}}]}
        ]
    )
    monkeypatch.setattr(DeezerClient, "search", search)
    menu = MagicMock(return_value=None)
    monkeypatch.setattr(TerminalMenu, "show", menu)
    monkeypatch.setattr(TerminalMenu, "__init__", lambda self, *args, **kwargs: None)
    assert asyncio.run(streamrip_search.run_search("glitter jkyl", num_results=10)) == 0
    menu.assert_called_once()
    assert not list(tmp_path.glob("*.mp3"))
    assert search.call_args.kwargs["limit"] == 10


@pytest.mark.parametrize("system", ["Windows", "Linux"])
def test_platform_menu_selection_resolves_chosen_media(tmp_path, monkeypatch, system):
    import sys
    from streamrip.client import DeezerClient
    from streamrip.config import Config
    from streamrip.rip.main import Main
    from simple_term_menu import TerminalMenu

    config = Config.defaults()
    config.session.deezer.arl = "TEST"
    config.session.downloads.folder = str(tmp_path)
    config.session.database.downloads_enabled = False
    config.session.database.failed_downloads_enabled = False
    monkeypatch.setattr(streamrip_search, "_search_config", lambda *_: config)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr("platform.system", lambda: system)

    async def login(self):
        self.logged_in = True

    monkeypatch.setattr(DeezerClient, "login", login)
    monkeypatch.setattr(
        DeezerClient,
        "search",
        AsyncMock(
            return_value=[
                {
                    "data": [
                        {"id": 7, "title": "Glitter", "artist": {"name": "Jkyl & Hyde"}}
                    ]
                }
            ]
        ),
    )
    chooser = MagicMock(side_effect=lambda results, **kwargs: [(results[0], 0)])
    if system == "Windows":
        monkeypatch.setitem(sys.modules, "pick", SimpleNamespace(pick=chooser))
    else:
        monkeypatch.setattr(TerminalMenu, "__init__", lambda *args, **kwargs: None)
        chooser = MagicMock(return_value=(0,))
        monkeypatch.setattr(TerminalMenu, "show", chooser)
    media = SimpleNamespace(download_path=str(tmp_path / "chosen.mp3"), rip=AsyncMock())
    pending = SimpleNamespace(id="7", resolve=AsyncMock(return_value=media))
    selected = []

    async def add_all(self, items):
        selected.extend(items)
        self.pending.append(pending)

    monkeypatch.setattr(Main, "add_all_by_id", add_all)
    monkeypatch.setattr("mutagen.File", lambda *_: SimpleNamespace())
    (tmp_path / "chosen.mp3").write_bytes(b"synthetic audio")
    assert asyncio.run(streamrip_search.run_search("glitter jkyl", num_results=5)) == 0
    assert selected == [("deezer", "track", "7")]
    media.rip.assert_awaited_once()
    chooser.assert_called_once()


def test_windows_interrupt_never_downloads(tmp_path, monkeypatch):
    import sys
    from streamrip.client import DeezerClient
    from streamrip.config import Config

    config = Config.defaults()
    config.session.deezer.arl = "TEST"
    config.session.downloads.folder = str(tmp_path)
    config.session.database.downloads_enabled = False
    config.session.database.failed_downloads_enabled = False
    monkeypatch.setattr(streamrip_search, "_search_config", lambda *_: config)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr("platform.system", lambda: "Windows")

    async def login(self):
        self.logged_in = True

    monkeypatch.setattr(DeezerClient, "login", login)
    monkeypatch.setattr(
        DeezerClient,
        "search",
        AsyncMock(
            return_value=[
                {"data": [{"id": 7, "title": "Glitter", "artist": {"name": "Artist"}}]}
            ]
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "pick",
        SimpleNamespace(pick=MagicMock(side_effect=KeyboardInterrupt)),
    )
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(streamrip_search.run_search("query"))
    assert not list(tmp_path.iterdir())
