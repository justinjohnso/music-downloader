from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.mark.parametrize("mode", ["--help", "--setup", "--set-arl"])
def test_cli_paths_do_not_import_qt(mode: str) -> None:
    script = f"""
import importlib.abc
import sys

class RejectQt(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "PyQt6" or fullname.startswith("PyQt6."):
            raise ImportError("Qt unavailable in this CLI environment")

sys.meta_path.insert(0, RejectQt())
from src import downloader
if {mode!r} != "--help":
    from src import config
    config.run_setup_wizard = lambda: None
    config.set_arl = lambda *args, **kwargs: None
sys.argv = ["mdl", {mode!r}]
downloader.main()
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    if mode == "--help":
        assert "--sync-db" in result.stdout
        assert "--set-arl" in result.stdout


@pytest.mark.parametrize("entrypoint", ["flag", "script"])
def test_gui_entrypoints_dispatch_to_launcher(monkeypatch, entrypoint: str) -> None:
    from src import downloader

    launcher = MagicMock()
    module = MagicMock(launch_gui=launcher)
    monkeypatch.setitem(sys.modules, "src.gui", module)
    monkeypatch.setattr(downloader, "launch_gui", launcher, raising=False)
    if entrypoint == "flag":
        monkeypatch.setattr(sys, "argv", ["mdl", "--gui"])
        downloader.main()
    else:
        downloader.main_gui()
    launcher.assert_called_once_with()


def test_selection_prompt_retries_and_skips(monkeypatch):
    from src.downloader import _prompt_for_candidate

    candidate = {"artist": "Artist", "title": "Track", "album": "Album"}
    answers = iter(["bad", "2", "1"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    assert _prompt_for_candidate("query", [candidate]) == 0
    monkeypatch.setattr("builtins.input", lambda *_: "s")
    assert _prompt_for_candidate("query", [candidate]) is None
    monkeypatch.setattr("builtins.input", lambda *_: "q")
    with pytest.raises(KeyboardInterrupt):
        _prompt_for_candidate("query", [candidate])


@pytest.mark.parametrize("flags", [[], ["--first-result"], ["--select"]])
def test_download_defaults_remain_noninteractive(monkeypatch, flags):
    from src import downloader
    from unittest.mock import AsyncMock

    download = AsyncMock()
    monkeypatch.setattr(downloader, "download_track", download)
    monkeypatch.setattr("src.config.load_config", lambda: {"deezer": {"arl": "test"}})
    monkeypatch.setattr("src.config.ensure_mdl_config_complete", lambda: None)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys, "argv", ["mdl", *flags, "query"])
    downloader.main()
    assert download.call_args.kwargs["selection_callback"] is None
    assert download.call_args.kwargs["result_limit"] == 10


def test_search_lists_results_without_downloading(monkeypatch, capsys):
    from src import downloader
    from unittest.mock import AsyncMock

    search = AsyncMock(
        return_value=[{"artist": "Artist", "title": "Track", "album": "Album"}]
    )
    monkeypatch.setattr("src.search.search_track_candidates", search)
    download = AsyncMock()
    monkeypatch.setattr(downloader, "download_track", download)
    monkeypatch.setattr("src.config.load_config", lambda: {"deezer": {"arl": "test"}})
    monkeypatch.setattr("src.config.ensure_mdl_config_complete", lambda: None)
    monkeypatch.setattr(
        sys, "argv", ["mdl", "--search", "--result-limit", "3", "query"]
    )
    downloader.main()
    assert "Album" in capsys.readouterr().out
    download.assert_not_called()
    assert search.call_args.kwargs["result_limit"] == 3


def test_explicit_streamrip_config_is_forwarded(monkeypatch):
    from src import downloader
    from unittest.mock import AsyncMock

    download = AsyncMock()
    monkeypatch.setattr(downloader, "download_track", download)
    monkeypatch.setattr("src.config.load_config", lambda: {"deezer": {"arl": "test"}})
    monkeypatch.setattr("src.config.ensure_mdl_config_complete", lambda: None)
    monkeypatch.setattr(
        sys, "argv", ["mdl", "--config", "/custom/streamrip.toml", "query"]
    )
    downloader.main()
    assert download.call_args.args[1] == "/custom/streamrip.toml"


def test_batch_json_reports_failure_with_exit_status(monkeypatch, tmp_path, capsys):
    import json
    from unittest.mock import AsyncMock
    from src import downloader
    from src.workflow import DownloadOutcome

    batch = tmp_path / "batch.txt"
    batch.write_text("# ignored\nfirst\nsecond\n")
    expand = AsyncMock(side_effect=[[{"query": "first"}], [{"query": "second"}]])
    queue = AsyncMock(
        return_value=[
            DownloadOutcome("first", "downloaded"),
            DownloadOutcome("second", "failed", "No match"),
        ]
    )
    monkeypatch.setattr("src.workflow.expand_input", expand)
    monkeypatch.setattr("src.workflow.run_queue", queue)
    monkeypatch.setattr("src.config.load_config", lambda: {"deezer": {"arl": "test"}})
    monkeypatch.setattr("src.config.ensure_mdl_config_complete", lambda: None)
    monkeypatch.setattr(
        sys, "argv", ["mdl", "--batch", str(batch), "--json", "--retries", "2"]
    )
    with pytest.raises(SystemExit) as error:
        downloader.main()
    assert error.value.code == 1
    assert [item["status"] for item in json.loads(capsys.readouterr().out)] == [
        "downloaded",
        "failed",
    ]
    assert queue.call_args.kwargs["retries"] == 2
