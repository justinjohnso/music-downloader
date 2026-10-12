from __future__ import annotations

import asyncio
import contextlib
import sys
from pathlib import Path
from typing import Any

import tomlkit
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QTabWidget,
    QSpinBox,
    QTextEdit,
    QScrollArea,
    QGroupBox,
    QFormLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QProgressBar,
    QSplitter,
    QAbstractItemView,
    QFileDialog,
    QDialog,
    QMessageBox,
)

from .config import (
    _secure_write,
    load_config_with_path,
    _get_mdl_config_path,
    _write_or_update_config,
    _validate_deezer_arl,
)
from .workflow import run_queue
from .search import search_track_candidates, format_track_candidate
from .spotify import is_spotify_link, get_spotify_tracks


class SignalWriter:
    def __init__(self, signal: Any) -> None:
        self.signal = signal

    def write(self, text: str) -> None:
        if text.strip():
            self.signal.emit(text.rstrip())

    def flush(self) -> None:
        pass


class Worker(QThread):
    progress = pyqtSignal(str)
    candidates = pyqtSignal(list)
    completed = pyqtSignal(bool, str)
    outcome = pyqtSignal(dict)

    def __init__(
        self,
        mode: str,
        query: str,
        verbose: bool = False,
        candidate: dict | None = None,
        limit: int = 10,
        engine_config_path: str | None = None,
        retries: int = 0,
    ) -> None:
        super().__init__()
        self.mode, self.query, self.verbose, self.candidate, self.limit = (
            mode,
            query,
            verbose,
            candidate,
            limit,
        )
        self.engine_config_path = engine_config_path
        self.retries = retries
        self.loop = None
        self.task = None
        self.cancel_requested = False

    async def execute(self) -> bool:
        if self.cancel_requested:
            raise asyncio.CancelledError
        if self.mode == "validate":
            return await asyncio.to_thread(_validate_deezer_arl, self.query)
        if self.mode == "search":
            if is_spotify_link(self.query):
                tracks, _ = await asyncio.to_thread(get_spotify_tracks, self.query)
                matches = []
                for track in tracks:
                    found = await search_track_candidates(
                        f"{track['artist']} {track['title']}",
                        config_path=self.engine_config_path,
                        result_limit=1,
                    )
                    matches.extend(found)
                self.candidates.emit(matches)
            else:
                self.candidates.emit(
                    await search_track_candidates(
                        self.query,
                        config_path=self.engine_config_path,
                        result_limit=self.limit,
                    )
                )
        elif self.candidate is not None:
            results = await run_queue(
                [{"query": self.query, "candidate": self.candidate}],
                config_path=self.engine_config_path,
                retries=self.retries,
                verbose=self.verbose,
                outcome_callback=lambda result: self.outcome.emit(result.to_dict()),
            )
            return results[0].status in ("downloaded", "skipped")
        elif self.mode == "download":
            from .workflow import expand_input

            results = await run_queue(
                await expand_input(self.query),
                config_path=self.engine_config_path,
                retries=self.retries,
                verbose=self.verbose,
                outcome_callback=lambda result: self.outcome.emit(result.to_dict()),
            )
            return bool(results) and all(
                result.status in ("downloaded", "skipped") for result in results
            )
        else:
            raise ValueError("Unknown worker operation")
        return True

    def run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            with contextlib.redirect_stdout(SignalWriter(self.progress)):
                self.task = self.loop.create_task(self.execute())
                success = self.loop.run_until_complete(self.task)
            self.completed.emit(
                success,
                "Finished; check the download log for per-track results."
                if success
                else "Download failed",
            )
        except asyncio.CancelledError:
            self.completed.emit(False, "Cancelled")
        except Exception as error:
            self.completed.emit(False, str(error) or type(error).__name__)
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.run_until_complete(self.loop.shutdown_default_executor())
            self.loop.close()

    def cancel(self) -> None:
        self.cancel_requested = True
        if (
            self.loop is not None
            and self.task is not None
            and not self.task.done()
            and not self.loop.is_closed()
        ):
            self.loop.call_soon_threadsafe(self.task.cancel)


class WorkerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None

    def reject(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
            return
        super().reject()

    def closeEvent(self, event) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
            event.ignore()
        else:
            event.accept()


class MainWindow(QWidget):
    def __init__(self, config_path: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Music Downloader")
        self.resize(1000, 720)
        self.worker = None
        self.queue_items = []
        self.queue_running = False
        self.active_row = None
        self.config_widgets = {}
        self.original_values = {}
        _, detected = load_config_with_path()
        self.config_path = Path(config_path or detected or _get_mdl_config_path())
        self.engine_config_path = None
        self.setStyleSheet(
            "QWidget { background: #002b36; color: #eee8d5; font-size: 13px; } QLineEdit,QTextEdit,QTreeWidget,QTableWidget,QSpinBox { background: #073642; padding: 6px; } QPushButton { background: #2aa198; color: #002b36; padding: 8px 14px; border-radius: 4px; } QPushButton:disabled { background: #586e75; } QGroupBox { border: 1px solid #586e75; margin-top: 18px; padding: 12px; } QTreeWidget::item:selected { background: #268bd2; } "
        )
        layout = QVBoxLayout(self)
        from importlib.metadata import version, PackageNotFoundError

        try:
            release_version = version("music-downloader")
        except PackageNotFoundError:
            release_version = "development"
        heading = QLabel(f"MUSIC DOWNLOADER  {release_version}")
        layout.addWidget(heading)
        engine_picker = QPushButton("Choose engine config")
        engine_picker.clicked.connect(self.choose_engine_config)
        layout.addWidget(engine_picker)
        self.engine_label = QLabel("Default engine config")
        layout.addWidget(self.engine_label)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        download = QWidget()
        controls = QVBoxLayout(download)
        self.query = QLineEdit()
        self.query.setPlaceholderText("Artist / track or Spotify link")
        controls.addWidget(self.query)
        buttons = QHBoxLayout()
        self.search_button = QPushButton("Search")
        self.download_button = QPushButton("Download")
        self.queue_button = QPushButton("Queue selected")
        self.cancel_button = QPushButton("Cancel")
        self.verbose = QCheckBox("Verbose output")
        self.limit = QSpinBox()
        self.limit.setRange(1, 200)
        self.limit.setValue(10)
        self.retries = QSpinBox()
        self.retries.setRange(0, 10)
        self.retries.setPrefix("Retries: ")
        for widget in (
            self.search_button,
            self.download_button,
            self.queue_button,
            self.cancel_button,
            self.verbose,
            self.limit,
            self.retries,
        ):
            buttons.addWidget(widget)
        controls.addLayout(buttons)
        self.results = QTreeWidget()
        self.results.setHeaderLabels(["Artist / album / track", "Duration", "Explicit"])
        self.results.setAlternatingRowColors(True)
        self.results.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.results)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.splitter.addWidget(self.log)
        controls.addWidget(self.splitter)
        self.show_log = QCheckBox("Show log")
        self.show_log.setChecked(True)
        self.show_log.toggled.connect(self.log.setVisible)
        controls.addWidget(self.show_log)
        self.tabs.addTab(download, "Download")
        queue = QWidget()
        queue_layout = QVBoxLayout(queue)
        self.queue_table = QTableWidget(0, 3)
        self.queue_table.setHorizontalHeaderLabels(["Track", "Status", "Progress"])
        self.queue_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.queue_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        queue_layout.addWidget(self.queue_table)
        self.start_button = QPushButton("Start queue")
        queue_layout.addWidget(self.start_button)
        batch = QPushButton("Import batch file")
        batch.clicked.connect(self.import_batch)
        queue_layout.addWidget(batch)
        export = QPushButton("Export JSON results")
        export.clicked.connect(self.export_results)
        queue_layout.addWidget(export)
        self.retry_button = QPushButton("Retry selected")
        self.retry_button.clicked.connect(self.retry_selected)
        queue_layout.addWidget(self.retry_button)
        self.rematch_button = QPushButton("Rematch selected")
        self.rematch_button.clicked.connect(self.rematch_selected)
        queue_layout.addWidget(self.rematch_button)
        self.tabs.addTab(queue, "Queue")
        self.build_config_tab()
        self.search_button.clicked.connect(self.search)
        self.download_button.clicked.connect(self.download)
        self.queue_button.clicked.connect(self.queue_selected)
        self.cancel_button.clicked.connect(self.cancel)
        self.start_button.clicked.connect(self.start_queue)
        self.query.returnPressed.connect(self.search)

    def build_config_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel(str(self.config_path)))
        setup = QPushButton("Run setup wizard")
        setup.clicked.connect(self.run_setup)
        layout.addWidget(setup)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        fields = QWidget()
        groups = QVBoxLayout(fields)
        try:
            document = tomlkit.parse(self.config_path.read_text(encoding="utf-8"))
            for section, values in document.items():
                if not isinstance(values, dict):
                    continue
                group = QGroupBox(section.upper())
                form = QFormLayout(group)
                for key, value in values.items():
                    if isinstance(value, bool):
                        widget = QCheckBox()
                        widget.setChecked(value)
                    elif isinstance(value, int) and -(2**31) <= value < 2**31:
                        widget = QSpinBox()
                        widget.setRange(-(2**31), 2**31 - 1)
                        widget.setValue(value)
                    elif isinstance(value, (str, float, list)):
                        widget = QLineEdit()
                        widget.setText(
                            tomlkit.dumps({"value": value}).split("=", 1)[1].strip()
                            if isinstance(value, list)
                            else str(value)
                        )
                        if any(
                            word in key
                            for word in ("arl", "secret", "token", "password")
                        ):
                            widget.setEchoMode(QLineEdit.EchoMode.Password)
                    else:
                        continue
                    self.config_widgets[(section, key)] = widget
                    self.original_values[(section, key)] = value
                    help_text = {
                        "arl": "Deezer credential; use a valid account cookie.",
                        "quality": "Deezer: 1 requests 320kbps MP3, 2 requests FLAC.",
                        "folder": "Audio output directory.",
                        "downloads_path": "SQLite download-history path.",
                        "failed_downloads_path": "SQLite failed-history path.",
                        "track_format": "Filename template; add {id} to avoid ambiguous names.",
                        "codec": "FFmpeg conversion codec; source file is removed after success.",
                        "verify_ssl": "Keep enabled for certificate verification.",
                        "max_connections": "Engine limit; current batch tracks remain sequential.",
                    }.get(
                        key,
                        f"{section}.{key}: see docs/configuration.md for supported behavior.",
                    )
                    widget.setToolTip(help_text)
                    form.addRow(key.replace("_", " ").title(), widget)
                groups.addWidget(group)
        except Exception:
            groups.addWidget(QLabel("No readable config. Run mdl --setup first."))
        scroll.setWidget(fields)
        layout.addWidget(scroll)
        save = QPushButton("Save Config")
        save.clicked.connect(self.save_config)
        layout.addWidget(save)
        self.config_status = QLabel("")
        layout.addWidget(self.config_status)
        self.tabs.addTab(tab, "Config")

    def run_setup(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        dialog = WorkerDialog(self)
        dialog.setWindowTitle("Setup")
        form = QFormLayout(dialog)
        try:
            existing = (
                tomlkit.parse(self.config_path.read_text(encoding="utf-8"))
                if self.config_path.exists()
                else {}
            )
        except Exception as error:
            self.config_status.setText(f"Error: {error}")
            return
        arl = QLineEdit(existing.get("deezer", {}).get("arl", ""))
        arl.setEchoMode(QLineEdit.EchoMode.Password)
        folder = QLineEdit(
            existing.get("downloads", {}).get(
                "folder", str(Path.home() / "Music" / "Music Downloader")
            )
        )
        quality = QSpinBox()
        quality.setRange(1, 2)
        quality.setValue(existing.get("deezer", {}).get("quality", 1))
        form.addRow("ARL", arl)
        form.addRow("Folder", folder)
        browse = QPushButton("Choose folder")
        browse.clicked.connect(
            lambda: folder.setText(
                QFileDialog.getExistingDirectory(
                    dialog, "Download folder", folder.text()
                )
                or folder.text()
            )
        )
        form.addRow(browse)
        form.addRow("Quality: 1 MP3, 2 FLAC", quality)
        save = QPushButton("Validate and save")
        form.addRow(save)

        validated_arl = ""

        def validated(success: bool, message: str) -> None:
            save.setEnabled(True)
            if dialog.worker.cancel_requested:
                return
            if not success:
                QMessageBox.warning(
                    dialog,
                    "Login failed",
                    "ARL validation failed. No config was saved.",
                )
                return
            try:
                _write_or_update_config(
                    self.config_path,
                    {
                        "arl": validated_arl,
                        "quality": quality.value(),
                        "folder": folder.text(),
                        "spotify_id": existing.get("spotify", {}).get("client_id", ""),
                        "spotify_secret": existing.get("spotify", {}).get(
                            "client_secret", ""
                        ),
                    },
                )
                dialog.accept()
                self.config_status.setText(
                    "Setup saved. Reopen the window to refresh config fields."
                )
            except Exception as error:
                QMessageBox.warning(dialog, "Save failed", str(error))

        def finish() -> None:
            nonlocal validated_arl
            if not arl.text().strip() or (
                dialog.worker is not None and dialog.worker.isRunning()
            ):
                return
            save.setEnabled(False)
            validated_arl = arl.text().strip()
            dialog.worker = Worker("validate", validated_arl)
            dialog.worker.setParent(dialog)
            dialog.worker.completed.connect(validated)
            dialog.worker.start()

        save.clicked.connect(finish)
        dialog.exec()

    def save_config(self) -> None:
        try:
            document = tomlkit.parse(self.config_path.read_bytes().decode("utf-8"))
            changed = []
            for (section, key), widget in self.config_widgets.items():
                original = self.original_values[(section, key)]
                if isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                elif isinstance(widget, QSpinBox):
                    value = widget.value()
                elif isinstance(original, list):
                    value = tomlkit.parse("value = " + widget.text())["value"]
                    if not isinstance(value, list):
                        raise ValueError(f"{section}.{key} requires an array")
                elif isinstance(original, float):
                    value = float(widget.text())
                else:
                    value = widget.text()
                if value != original:
                    document[section][key] = value
                    changed.append(((section, key), value))
            if changed:
                _secure_write(self.config_path, tomlkit.dumps(document))
                for key, value in changed:
                    self.original_values[key] = value
            self.config_status.setText("Config saved")
        except Exception as error:
            self.config_status.setText(f"Error: {error}")

    def show_candidates(self, candidates: list[dict]) -> None:
        self.results.clear()
        artists = {}
        albums = {}
        for candidate in candidates:
            artist = candidate["artist"]
            album_key = (artist, candidate["album"])
            if artist not in artists:
                artists[artist] = QTreeWidgetItem(self.results, [artist])
            if album_key not in albums:
                albums[album_key] = QTreeWidgetItem(
                    artists[artist], [candidate["album"]]
                )
            item = QTreeWidgetItem(
                albums[album_key],
                [
                    candidate["title"],
                    f"{candidate['duration'] // 60}:{candidate['duration'] % 60:02d}"
                    if isinstance(candidate.get("duration"), int)
                    and candidate["duration"] > 0
                    else "",
                    "Yes" if candidate.get("explicit") else "No",
                ],
            )
            item.setData(0, Qt.ItemDataRole.UserRole, candidate)
        self.results.expandAll()

    def selected_candidates(self) -> list[dict]:
        candidates = {}

        def collect(item) -> None:
            value = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(value, dict):
                candidates.setdefault(value["id"], value)
            for index in range(item.childCount()):
                collect(item.child(index))

        for item in self.results.selectedItems():
            collect(item)
        return list(candidates.values())

    def start_worker(
        self, mode: str, query: str, candidate: dict | None = None
    ) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        self.worker = Worker(
            mode,
            query,
            self.verbose.isChecked(),
            candidate,
            self.limit.value(),
            self.engine_config_path,
            self.retries.value(),
        )
        self.worker.progress.connect(self.log.append)
        self.worker.candidates.connect(self.show_candidates)
        self.worker.completed.connect(self.worker_completed)
        self.worker.outcome.connect(self.record_outcome)
        self.worker.finished.connect(self.queue_after_worker)
        self.start_button.setEnabled(False)
        self.search_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.worker.start()

    def import_batch(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Batch file", "", "Text files (*.txt)"
        )
        if not path:
            return
        try:
            values = [
                line.strip()
                for line in Path(path).read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
            for value in values:
                self.queue_items.append({"query": value, "status": "Pending"})
                row = self.queue_table.rowCount()
                self.queue_table.insertRow(row)
                self.queue_table.setItem(row, 0, QTableWidgetItem(value))
                self.queue_table.setItem(row, 1, QTableWidgetItem("Pending"))
                progress = QProgressBar()
                progress.setRange(0, 100)
                self.queue_table.setCellWidget(row, 2, progress)
        except Exception as error:
            self.log.append(f"Batch import failed: {error}")

    def export_results(self) -> None:
        import json

        path, _ = QFileDialog.getSaveFileName(
            self, "Queue results", "results.json", "JSON files (*.json)"
        )
        if path:
            try:
                _secure_write(
                    Path(path),
                    json.dumps(
                        [
                            outcome
                            for item in self.queue_items
                            for outcome in item.get("outcomes", [])
                        ],
                        indent=2,
                    ),
                )
            except Exception as error:
                self.log.append(f"Result export failed: {error}")

    def choose_engine_config(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Streamrip config", "", "TOML files (*.toml)"
        )
        if path:
            self.engine_config_path = path
            self.engine_label.setText(path)

    def record_outcome(self, outcome: dict) -> None:
        if self.active_row is not None:
            self.queue_items[self.active_row].setdefault("outcomes", []).append(outcome)
            self.queue_items[self.active_row]["outcome"] = outcome
            statuses = [
                result["status"]
                for result in self.queue_items[self.active_row]["outcomes"]
            ]
            self.queue_items[self.active_row]["status"] = (
                "failed" if "failed" in statuses else outcome["status"]
            )
            self.queue_table.item(self.active_row, 1).setText(
                self.queue_items[self.active_row]["status"]
            )

    def search(self) -> None:
        if self.query.text().strip():
            self.start_worker("search", self.query.text().strip())

    def download(self) -> None:
        selected = self.selected_candidates()
        if selected:
            self.queue_selected()
            self.start_queue()
        elif self.query.text().strip():
            self.search()

    def queue_selected(self) -> None:
        for candidate in self.selected_candidates():
            if any(
                item.get("candidate", {}).get("id") == candidate["id"]
                for item in self.queue_items
            ):
                continue
            self.queue_items.append({"candidate": candidate, "status": "Pending"})
            row = self.queue_table.rowCount()
            self.queue_table.insertRow(row)
            self.queue_table.setItem(
                row, 0, QTableWidgetItem(format_track_candidate(candidate))
            )
            self.queue_table.setItem(row, 1, QTableWidgetItem("Pending"))
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(0)
            self.queue_table.setCellWidget(row, 2, progress)

    def replace_queue_candidate(self, row: int, candidate: dict) -> None:
        self.queue_items[row].pop("outcome", None)
        self.queue_items[row].pop("outcomes", None)
        self.queue_items[row]["candidate"] = candidate
        self.queue_items[row]["status"] = "Pending"
        self.queue_table.item(row, 0).setText(format_track_candidate(candidate))
        self.queue_table.item(row, 1).setText("Pending")
        self.queue_table.cellWidget(row, 2).setRange(0, 100)
        self.queue_table.cellWidget(row, 2).setValue(0)

    def retry_selected(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        for selected in self.queue_table.selectionModel().selectedRows():
            row = selected.row()
            self.queue_items[row].pop("outcome", None)
            self.queue_items[row].pop("outcomes", None)
            if "candidate" in self.queue_items[row]:
                self.replace_queue_candidate(row, self.queue_items[row]["candidate"])
            else:
                self.queue_items[row]["status"] = "Pending"
                self.queue_table.item(row, 1).setText("Pending")

    def rematch_selected(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        rows = self.queue_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        candidate = self.queue_items[row].get("candidate") or {
            "artist": "",
            "title": self.queue_items[row]["query"],
        }
        dialog = WorkerDialog(self)
        dialog.setWindowTitle("Rematch track")
        layout = QVBoxLayout(dialog)
        query = QLineEdit(f"{candidate['artist']} {candidate['title']}")
        layout.addWidget(query)
        search = QPushButton("Search matches")
        layout.addWidget(search)
        choices = QTreeWidget()
        choices.setHeaderLabels(["Match"])
        layout.addWidget(choices)
        select = QPushButton("Use selected match")
        select.setEnabled(False)
        layout.addWidget(select)
        worker = None

        def found(candidates) -> None:
            choices.clear()
            for result in candidates:
                item = QTreeWidgetItem(choices, [format_track_candidate(result)])
                item.setData(0, Qt.ItemDataRole.UserRole, result)
            select.setEnabled(bool(candidates))

        def begin() -> None:
            nonlocal worker
            if worker is not None and worker.isRunning():
                return
            worker = Worker(
                "search",
                query.text(),
                self.verbose.isChecked(),
                limit=self.limit.value(),
                engine_config_path=self.engine_config_path,
            )
            dialog.worker = worker
            worker.setParent(dialog)
            worker.candidates.connect(found)
            worker.completed.connect(
                lambda success, message: (
                    self.log.append(message) if not success else None
                )
            )
            worker.start()

        def choose() -> None:
            item = choices.currentItem()
            if item is not None:
                self.replace_queue_candidate(
                    row, item.data(0, Qt.ItemDataRole.UserRole)
                )
                dialog.accept()

        search.clicked.connect(begin)
        select.clicked.connect(choose)
        dialog.exec()

    def start_queue(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        self.queue_running = True
        self.next_queued()

    def next_queued(self) -> None:
        for row, item in enumerate(self.queue_items):
            if item["status"] == "Pending":
                self.active_row = row
                item["status"] = "Running"
                self.queue_table.item(row, 1).setText("Running")
                self.queue_table.cellWidget(row, 2).setRange(0, 0)
                self.start_worker(
                    "download",
                    format_track_candidate(item["candidate"])
                    if "candidate" in item
                    else item["query"],
                    item.get("candidate"),
                )
                return
        self.queue_running = False

    def worker_completed(self, success: bool, message: str) -> None:
        self.log.append(message)
        self.search_button.setEnabled(True)
        self.download_button.setEnabled(True)
        if self.active_row is not None:
            if "outcome" not in self.queue_items[self.active_row]:
                self.queue_items[self.active_row]["status"] = (
                    "cancelled" if message == "Cancelled" else "failed"
                )
            self.queue_table.item(self.active_row, 1).setText(
                self.queue_items[self.active_row]["status"]
            )
            self.queue_table.cellWidget(self.active_row, 2).setRange(0, 100)
            self.queue_table.cellWidget(self.active_row, 2).setValue(
                100 if success else 0
            )
            self.active_row = None

    def queue_after_worker(self) -> None:
        self.start_button.setEnabled(True)
        if self.queue_running:
            self.next_queued()

    def cancel(self) -> None:
        self.queue_running = False
        if self.worker is not None:
            self.worker.cancel()

    def closeEvent(self, event: Any) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.cancel()
            event.ignore()
            self.log.append("Cancelling active work; close again after it finishes.")
        else:
            event.accept()


def launch_gui() -> None:
    application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(application.exec())
