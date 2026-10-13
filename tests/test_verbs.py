import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.parametrize(
    "arguments",
    [
        ["--help"],
        ["search", "--help"],
        ["download", "--help"],
        ["auth", "--help"],
        ["library", "--help"],
        ["--version"],
        ["--verbose", "--help"],
        ["-c/custom/config.toml", "search", "--help"],
    ],
)
def test_help_and_version_do_not_load_config(monkeypatch, arguments):
    from src import downloader

    monkeypatch.setattr(
        "src.config.load_config",
        MagicMock(side_effect=AssertionError("No config reads for help")),
    )
    monkeypatch.setattr(sys, "argv", ["mdl", *arguments])
    with pytest.raises(SystemExit) as error:
        downloader.main()
    assert error.value.code == 0


def test_bare_spotify_keeps_default_download_dispatch(monkeypatch):
    from src import downloader

    run = MagicMock()
    monkeypatch.setattr(downloader, "legacy_main", run)
    monkeypatch.setattr(sys, "argv", ["mdl", "https://open.spotify.com/track/test"])
    downloader.main()
    assert run.call_count == 1


def test_search_is_interactive_by_default_and_uses_deezer(monkeypatch):
    from src import downloader

    search = AsyncMock(return_value=0)
    monkeypatch.setattr("src.streamrip_search.run_search", search)
    monkeypatch.setattr(sys, "argv", ["mdl", "search", "glitter jkyl"])
    downloader.main()
    assert search.call_args.args[0] == "glitter jkyl"
    assert search.call_args.kwargs["media_type"] == "track"
    assert search.call_args.kwargs["first"] is False


def test_maintenance_verbs_dispatch_existing_operations(monkeypatch):
    from src import downloader

    refresh = MagicMock()
    monkeypatch.setattr("src.config.set_arl", refresh)
    monkeypatch.setattr(sys, "argv", ["mdl", "auth", "refresh", "NEW"])
    downloader.main()
    refresh.assert_called_once_with("NEW", verbose=False)
