from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main() -> None:
    """Exercise the installed GUI entrypoint without credentials or downloads."""
    with tempfile.TemporaryDirectory(prefix="mdl-smoke-") as temporary_dir:
        root = Path(temporary_dir)
        os.environ["HOME"] = str(root)
        os.environ["USERPROFILE"] = str(root)
        os.environ["APPDATA"] = str(root)
        os.environ["XDG_CONFIG_HOME"] = str(root)
        os.environ["XDG_DATA_HOME"] = str(root)

        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication, QPushButton, QTabWidget
        from src.config import _write_or_update_config
        from src.downloader import main_gui
        from src.schema import STREAMRIP_SECTIONS

        config_path = root / "mdl-config.toml"
        _write_or_update_config(
            config_path,
            {
                "arl": "TESTARL",
                "quality": 1,
                "folder": str(root / "music"),
                "spotify_id": "",
                "spotify_secret": "",
            },
        )
        assert len(STREAMRIP_SECTIONS) == 15
        before = config_path.read_bytes()
        observed = []
        failures = []
        original_exec = QApplication.exec

        def inspect_window() -> None:
            application = QApplication.instance()
            try:
                windows = [
                    window
                    for window in application.topLevelWidgets()
                    if window.windowTitle() == "Music Downloader"
                ]
                assert len(windows) == 1
                window = windows[0]
                tabs = window.findChild(QTabWidget)
                assert [tabs.tabText(index) for index in range(tabs.count())] == [
                    "Download",
                    "Queue",
                    "Config",
                ]
                assert any(
                    button.text() == "Download"
                    for button in window.findChildren(QPushButton)
                )
                observed.append(True)
                window.close()
            except Exception as error:
                failures.append(error)
            finally:
                application.quit()

        def timed_exec(application: QApplication) -> int:
            QTimer.singleShot(0, inspect_window)
            QTimer.singleShot(5000, application.quit)
            return original_exec()

        with (
            patch("src.config._get_mdl_config_path", return_value=config_path),
            patch.object(QApplication, "exec", timed_exec),
        ):
            try:
                main_gui()
            except SystemExit as error:
                assert error.code == 0
        if failures:
            raise failures[0]
        assert observed == [True]
        assert config_path.read_bytes() == before
        print("Installed GUI and config smoke passed")


if __name__ == "__main__":
    main()
