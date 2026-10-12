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
