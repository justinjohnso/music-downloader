import sys
import io
import asyncio
import os
import traceback
from importlib.metadata import PackageNotFoundError, version as get_version
from pathlib import Path
from typing import Optional, List, Dict, Any

import tomlkit
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QUrl, QSize
from PyQt6.QtGui import QDesktopServices, QColor, QPalette, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QProgressBar,
    QAbstractItemView,
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
)

# ... (rest of imports)

from .config import (
    _get_mdl_config_path,
    ensure_streamrip_config_exists,
    load_config_with_path,
)
from .core import (
    download_track_candidate,
    format_track_candidate,
    process_spotify_link,
    search_track_candidates,
    TrackCandidate,
)
from .spotify import get_spotify_tracks, is_spotify_link

# -- Solarized Dark Tokens (Accessible Overrides) --
# Backgrounds
S_BASE03 = "#002b36"  # Main background
S_BASE02 = "#073642"  # Highlight background
S_BASE01 = "#586e75"  # Comments / secondary text

# Foreground
S_BASE0 = "#839496"   # Body text (Main)
S_BASE1 = "#93a1a1"   # Primary text (Better contrast)
S_BASE2 = "#eee8d5"   # Heading text (Strong contrast)

# Accents
S_YELLOW = "#b58900"
S_ORANGE = "#cb4b16"
S_RED = "#dc322f"
S_MAGENTA = "#d33682"
S_VIOLET = "#6c71c4"
S_BLUE = "#268bd2"
S_CYAN = "#2aa198"
S_GREEN = "#859900"

# -- Fonts --
S_SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'
S_MONO = '"SF Mono", "JetBrains Mono", "Fira Code", "Menlo", "Consolas", monospace'

# -- Configuration Tooltips (sourced from streamrip) --
TOOLTIPS = {
    "folder": "The absolute path where your downloads will be saved.",
    "source_subdirectories": "Create subfolders for each source (e.g., /Downloads/Deezer/).",
    "concurrency": "Enable downloading and converting multiple tracks simultaneously.",
    "max_connections": "The maximum number of simultaneous downloads. Set to -1 for no limit.",
    "requests_per_minute": "Rate limiting for API requests to prevent account flagging.",
    "folder_format": "Template for album folders (e.g. {artist} - {title}).",
    "track_format": "Template for track filenames.",
    "restrict_characters": "Replace non-ASCII characters with underscores for compatibility.",
    "truncate": "Limit filename length to 120 characters to avoid OS errors.",
    "embed": "Write the album cover directly into the audio file metadata.",
    "embed_size": "Size of embedded artwork: thumbnail, small, large, or original.",
    "save_artwork": "Save the high-quality cover as a separate .jpg file.",
    "set_playlist_to_album": "Sets the ALBUM tag to the playlist name.",
    "renumber_playlist_tracks": "Replace original track number with playlist position.",
    "arl": "Deezer authentication cookie. Required for downloads.",
    "quality": "0=128kbps, 1=320kbps, 2=CD, 3=Hi-Res, 4=Ultra Hi-Res.",
}

def get_stylesheet() -> str:
    return f"""
        QWidget {{
            background-color: {S_BASE03};
            color: {S_BASE1};
            font-family: {S_SANS};
            font-size: 13px;
        }}
        
        QTabWidget::pane {{
            border: 1px solid {S_BASE02};
            top: -1px;
            background-color: {S_BASE03};
            border-radius: 8px;
            border-top-left-radius: 0px;
        }}
        
        QTabBar::tab {{
            background: {S_BASE02};
            color: {S_BASE0};
            padding: 10px 24px;
            margin-right: 4px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: 600;
        }}
        
        QTabBar::tab:selected {{
            background: {S_BASE03};
            color: {S_BASE2};
            border-bottom: 2px solid {S_YELLOW};
        }}
        
        QGroupBox {{
            border: 1px solid {S_BASE02};
            border-radius: 8px;
            margin-top: 24px;
            font-weight: bold;
            color: {S_YELLOW};
            padding-top: 24px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
        }}
        
        QLineEdit, QTextEdit, QSpinBox {{
            background-color: #00212b;
            border: 1px solid {S_BASE02};
            border-radius: 6px;
            color: {S_BASE2};
            padding: 8px 12px;
            font-family: {S_MONO};
        }}
        
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 0px;
            border: none;
        }}
        
        QCheckBox, QRadioButton {{
            spacing: 8px;
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid {S_BASE01};
            background-color: #00212b;
        }}

        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background-color: {S_BLUE};
            border-color: {S_BLUE};
        }}

        QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {{
            border: 1px solid {S_BLUE};
            background-color: {S_BASE02};
        }}
        
        QPushButton {{
            background-color: {S_BLUE};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 24px;
            font-weight: 600;
        }}
        
        QPushButton:hover {{
            background-color: #2e9fdf;
        }}
        
        QPushButton#secondaryButton {{
            background-color: transparent;
            color: {S_BASE1};
            border: 1px solid {S_BASE01};
            padding: 6px 16px;
        }}
        
        QPushButton#secondaryButton:hover {{
            background-color: {S_BASE02};
            color: {S_BASE2};
        }}
        
        QTreeWidget {{
            background-color: {S_BASE03};
            border: 1px solid {S_BASE02};
            border-radius: 8px;
            outline: none;
            font-family: {S_MONO};
        }}
        
        QTreeWidget::item {{
            padding: 12px;
            border-bottom: 1px solid {S_BASE02};
        }}

        QTreeWidget::item:selected {{
            background-color: {S_BASE02};
            color: {S_YELLOW};
        }}

        /* Artist Level */
        QTreeWidget::item[level="0"] {{
            background-color: #003642;
            font-weight: bold;
            color: {S_YELLOW};
        }}

        /* Album Level */
        QTreeWidget::item[level="1"] {{
            background-color: #002b36;
            color: {S_CYAN};
            padding-left: 20px;
        }}

        QHeaderView::section {{
            background-color: {S_BASE02};
            color: {S_BASE0};
            padding: 12px;
            border: none;
            border-bottom: 1px solid {S_BASE01};
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 11px;
        }}
        
        QProgressBar {{
            border: none;
            border-radius: 3px;
            background-color: #001e26;
            height: 6px;
        }}
        
        QProgressBar::chunk {{
            background-color: {S_CYAN};
            border-radius: 3px;
        }}
        
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 10px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {S_BASE02};
            min-height: 40px;
            border-radius: 5px;
            margin: 2px;
        }}
        
        #consoleLog {{
            background-color: #001e26;
            border: none;
            border-top: 1px solid {S_BASE02};
            font-family: {S_MONO};
            font-size: 12px;
            color: {S_BASE0};
            padding: 16px;
        }}

        QToolTip {{
            background-color: {S_BASE02};
            color: {S_BASE2};
            border: 1px solid {S_BASE01};
            padding: 8px;
            border-radius: 4px;
        }}
    """

class SearchThread(QThread):
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, query: str, verbose: bool, limit: int = 20):
        super().__init__()
        self.query = query
        self.verbose = verbose
        self.limit = limit
        self.loop = None
        self.task = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        async def run_search_logic():
            if not is_spotify_link(self.query):
                candidates = await search_track_candidates(self.query, None, self.verbose, result_limit=self.limit)
                return {"mode": "candidates", "query": self.query, "candidates": candidates}
            
            # Spotify handling
            tracks, info = await asyncio.get_event_loop().run_in_executor(
                None, get_spotify_tracks, self.query
            )
            is_playlist = bool(info.get("is_playlist")) if isinstance(info, dict) else False
            
            if is_playlist or len(tracks) > 1:
                return {"mode": "spotify_playlist", "tracks": tracks, "info": info}
            
            if not tracks:
                return {"mode": "candidates", "query": self.query, "candidates": []}
                
            track = tracks[0]
            deezer_query = f"{track.get('artist', '')} {track.get('title', '')}".strip()
            candidates = await search_track_candidates(deezer_query, None, self.verbose, result_limit=self.limit)
            return {"mode": "candidates", "query": deezer_query, "candidates": candidates}

        self.task = self.loop.create_task(run_search_logic())
        try:
            self.loop.run_until_complete(self.task)
            result = self.task.result()
            self.result_signal.emit(result)
        except Exception as e:
            traceback.print_exc()
            self.error_signal.emit(str(e))
        finally:
            self.loop.close()

class DownloadThread(QThread):
    """Handles individual or batch downloads with progress reporting."""
    progress_signal = pyqtSignal(dict)  # { "id": str, "status": str, "progress": int, "message": str }
    
    def __init__(self, items: List[Dict[str, Any]], verbose: bool):
        super().__init__()
        self.items = items # List of candidates or spotify track info
        self.verbose = verbose
        self.loop = None
        self.task = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        async def run_downloads():
            for i, item in enumerate(self.items):
                # Unique ID for tracking in the UI
                ui_id = item.get("id") or f"sp_{item.get('artist')}_{item.get('title')}"
                display_name = f"{item.get('artist', 'Unknown')} - {item.get('title', 'Unknown')}"
                
                self.progress_signal.emit({
                    "id": ui_id, 
                    "status": "Downloading", 
                    "progress": 10, 
                    "message": f"Starting {display_name}..."
                })
                
                try:
                    candidate = item
                    # If it's a Spotify track (no Deezer ID), search for the first match
                    if not item.get("id"):
                        self.progress_signal.emit({
                            "id": ui_id, 
                            "status": "Matching", 
                            "progress": 20, 
                            "message": f"Searching Deezer for {display_name}..."
                        })
                        search_query = f"{item.get('artist')} {item.get('title')}"
                        candidates = await search_track_candidates(search_query, None, self.verbose, result_limit=1)
                        if not candidates:
                            raise Exception("No Deezer match found.")
                        candidate = candidates[0]

                    # Perform download
                    result = await download_track_candidate(candidate, None, self.verbose)
                    
                    if result:
                        self.progress_signal.emit({
                            "id": ui_id, 
                            "status": "Completed", 
                            "progress": 100, 
                            "message": f"Saved to {result}"
                        })
                    else:
                        raise Exception("Download failed (check logs).")
                        
                except Exception as e:
                    self.progress_signal.emit({
                        "id": ui_id, 
                        "status": "Failed", 
                        "progress": 0, 
                        "message": str(e)
                    })
                
                if i < len(self.items) - 1:
                    await asyncio.sleep(1) # Rate limiting

        self.task = self.loop.create_task(run_downloads())
        try:
            self.loop.run_until_complete(self.task)
        except Exception as e:
            print(f"Download thread error: {e}")
        finally:
            self.loop.close()

from PyQt6.QtWidgets import QDialog

from PyQt6.QtWidgets import QDialog, QRadioButton, QButtonGroup, QFileDialog

class SetupWizardDialog(QDialog):
    """A native GUI version of the setup wizard."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Music Downloader Setup")
        self.setMinimumSize(500, 450)
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(24)

        # Title
        title = QLabel("Initial Setup")
        title.setFont(QFont("-apple-system", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {S_BASE2};")
        self.layout.addWidget(title)

        # Description
        desc = QLabel("Configure your download settings and authentication.")
        desc.setStyleSheet(f"color: {S_BASE1};")
        self.layout.addWidget(desc)

        self.form = QFormLayout()
        self.form.setSpacing(16)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        # 1. Deezer ARL
        self.arl_input = QLineEdit()
        self.arl_input.setPlaceholderText("Paste your Deezer ARL cookie here...")
        arl_label = QLabel("Deezer ARL:")
        arl_label.setToolTip("Required for downloading. Expires every 3-4 months.")
        self.form.addRow(arl_label, self.arl_input)

        # 2. Download Folder
        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setText(os.path.expanduser("~/Music/Music Downloader"))
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setObjectName("secondaryButton")
        self.browse_btn.setFixedWidth(80)
        self.browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.browse_btn)
        self.form.addRow("Download Folder:", folder_layout)

        # 3. Quality
        self.quality_group = QButtonGroup(self)
        quality_layout = QHBoxLayout()
        
        self.q_mp3 = QRadioButton("320kbps MP3")
        self.q_mp3.setChecked(True)
        self.q_flac = QRadioButton("FLAC")
        
        self.quality_group.addButton(self.q_mp3, 1)
        self.quality_group.addButton(self.q_flac, 2)
        
        quality_layout.addWidget(self.q_mp3)
        quality_layout.addWidget(self.q_flac)
        quality_layout.addStretch()
        self.form.addRow("Audio Quality:", quality_layout)

        self.layout.addLayout(self.form)
        self.layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.finish_btn = QPushButton("Finish Setup")
        self.finish_btn.clicked.connect(self.finish_setup)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.finish_btn)
        self.layout.addLayout(btn_layout)

        self.setLayout(self.layout)

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.folder_input.text())
        if path:
            self.folder_input.setText(path)

    def finish_setup(self):
        arl = self.arl_input.text().strip()
        if not arl:
            QMessageBox.warning(self, "Required Field", "Deezer ARL is required to download music.")
            return

        folder = self.folder_input.text().strip()
        quality = self.quality_group.checkedId()

        from .config import _build_config_toml, _get_mdl_config_path, ensure_streamrip_config_exists, merge_mdl_config_into_streamrip
        
        config_content = _build_config_toml(arl, quality, folder)
        config_path = _get_mdl_config_path()
        
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(config_content)
            
            sr_path = ensure_streamrip_config_exists()
            merge_mdl_config_into_streamrip(sr_path, tomlkit.parse(config_content))
            
            QMessageBox.information(self, "Success", "Configuration saved successfully!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save configuration: {e}")

class RematchDialog(QDialog):
    def __init__(self, parent, query: str, verbose: bool):
        super().__init__(parent)
        self.query = query
        self.verbose = verbose
        self.selected_candidate = None
        self.search_thread = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Rematch Track")
        self.setMinimumSize(600, 450)
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel(f"Select a Deezer match for: {self.query}"))
        
        self.results_list = QListWidget()
        layout.addWidget(self.results_list)
        
        self.status_label = QLabel("Searching...")
        layout.addWidget(self.status_label)
        
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.select_btn = QPushButton("Download This Instead")
        self.select_btn.setEnabled(False)
        self.select_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.select_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.perform_search()

    def perform_search(self):
        self.search_thread = SearchThread(self.query, self.verbose)
        self.search_thread.result_signal.connect(self.on_results)
        self.search_thread.error_signal.connect(self.on_error)
        self.search_thread.start()

    def on_results(self, payload: dict):
        candidates = payload.get("candidates", [])
        self.candidates = candidates
        self.results_list.clear()
        if not candidates:
            self.status_label.setText("No results found.")
            return
            
        for c in candidates:
            dur = c.get("duration", 0)
            mins, secs = divmod(dur, 60)
            explicit = " [E]" if c.get("explicit") else ""
            label = f"{c.get('artist')} - {c.get('title')} ({c.get('album')}) [{mins}:{secs:02d}]{explicit}"
            self.results_list.addItem(label)
            
        self.results_list.setCurrentRow(0)
        self.select_btn.setEnabled(True)
        self.status_label.setText(f"Found {len(candidates)} candidates.")

    def on_error(self, error: str):
        self.status_label.setText(f"Error: {error}")

    def get_selected_candidate(self) -> Optional[dict]:
        row = self.results_list.currentRow()
        if row >= 0 and row < len(self.candidates):
            return self.candidates[row]
        return None

class SearchTab(QWidget):
    download_requested = pyqtSignal(list) # List of candidates to download

    def __init__(self, verbose_check: QCheckBox):
        super().__init__()
        self.verbose_check = verbose_check
        self.current_candidates: List[TrackCandidate] = []
        self.search_thread = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(12)
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Search artist, track, or paste Spotify link...")
        self.query_input.setMinimumHeight(44)
        self.query_input.returnPressed.connect(self.start_search)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.setMinimumHeight(44)
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self.start_search)
        
        search_layout.addWidget(self.query_input)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        # Filters/Options
        options_layout = QHBoxLayout()
        options_layout.setSpacing(12)
        options_layout.addWidget(QLabel("Result Limit:"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 100)
        self.limit_spin.setValue(20)
        self.limit_spin.setFixedWidth(70)
        self.limit_spin.setMinimumHeight(32)
        options_layout.addWidget(self.limit_spin)
        options_layout.addStretch()
        layout.addLayout(options_layout)

        # Results tree (Grouped by Artist)
        self.results_tree = QTreeWidget()
        self.results_tree.setColumnCount(4)
        self.results_tree.setHeaderLabels(["Title / Artist", "Album", "Duration", "Explicit"])
        self.results_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.results_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.results_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.results_tree.setIndentation(20)
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setAnimated(True)
        layout.addWidget(self.results_tree)

        # Action bar
        action_layout = QHBoxLayout()
        self.download_btn = QPushButton("Download Selected")
        self.download_btn.setEnabled(False)
        self.download_btn.setMinimumHeight(40)
        self.download_btn.setFixedWidth(200)
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.clicked.connect(self.on_download_clicked)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"color: {S_BASE01}; font-family: {S_MONO}; font-size: 11px;")
        
        action_layout.addWidget(self.status_label)
        action_layout.addStretch()
        action_layout.addWidget(self.download_btn)
        layout.addLayout(action_layout)

        self.setLayout(layout)

    def start_search(self):
        query = self.query_input.text().strip()
        if not query:
            return

        if self.search_thread and self.search_thread.isRunning():
            return

        self.status_label.setText("Searching...")
        self.search_btn.setEnabled(False)
        self.results_tree.clear()
        self.download_btn.setEnabled(False)

        try:
            self.search_thread = SearchThread(
                query, 
                self.verbose_check.isChecked(),
                limit=self.limit_spin.value()
            )
            self.search_thread.result_signal.connect(self.on_search_results)
            self.search_thread.error_signal.connect(self.on_search_error)
            self.search_thread.start()
        except Exception as e:
            self.on_search_error(str(e))

    def on_search_results(self, payload: dict):
        try:
            self.search_btn.setEnabled(True)
            mode = payload.get("mode")
            
            if mode == "spotify_playlist":
                tracks = payload.get("tracks", [])
                info = payload.get("info", {})
                name = info.get("name", "Playlist")
                count = len(tracks)
                
                choice = QMessageBox.question(
                    self, "Spotify Playlist",
                    f"Found playlist '{name}' with {count} tracks.\n\n"
                    "Download all tracks using automatic matching?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if choice == QMessageBox.StandardButton.Yes:
                    self.download_requested.emit(tracks)
                    self.status_label.setText(f"Sent {count} tracks to queue.")
                else:
                    self.status_label.setText("Search cancelled.")
                return

            self.current_candidates = payload.get("candidates", [])
            if not self.current_candidates:
                self.status_label.setText("No results found.")
                return

            # Group by artist and then album
            grouped = {}
            for c in self.current_candidates:
                artist_name = c.get("artist", "Unknown Artist")
                album_name = c.get("album", "Unknown Album")
                if artist_name not in grouped:
                    grouped[artist_name] = {}
                if album_name not in grouped[artist_name]:
                    grouped[artist_name][album_name] = []
                grouped[artist_name][album_name].append(c)

            for artist_name, albums in grouped.items():
                artist_item = QTreeWidgetItem(self.results_tree)
                artist_item.setText(0, artist_name)
                artist_item.setFont(0, QFont(S_SANS, 13, QFont.Weight.Bold))
                artist_item.setData(0, Qt.ItemDataRole.UserRole, "artist")
                artist_item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, "0") # level property for CSS
                artist_item.setFirstColumnSpanned(True)
                artist_item.setExpanded(True)
                
                for album_name, tracks in albums.items():
                    album_item = QTreeWidgetItem(artist_item)
                    album_item.setText(0, album_name)
                    album_item.setFont(0, QFont(S_SANS, 12, QFont.Weight.Medium))
                    album_item.setData(0, Qt.ItemDataRole.UserRole, "album")
                    album_item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, "1") # level property for CSS
                    album_item.setFirstColumnSpanned(True)
                    album_item.setExpanded(True)
                    
                    for t in tracks:
                        track_item = QTreeWidgetItem(album_item)
                        track_item.setText(0, t.get("title", ""))
                        
                        dur = t.get("duration", 0)
                        mins, secs = divmod(dur, 60)
                        track_item.setText(2, f"{mins}:{secs:02d}")
                        
                        explicit = "Yes" if t.get("explicit") else "No"
                        track_item.setText(3, explicit)
                        track_item.setData(0, Qt.ItemDataRole.UserRole, t)

            self.download_btn.setEnabled(True)
            self.status_label.setText(f"Found {len(self.current_candidates)} results.")
        except Exception as e:
            self.on_search_error(str(e))

    def on_search_error(self, error: str):
        traceback.print_exc()
        self.search_btn.setEnabled(True)
        self.status_label.setText("Search failed.")
        QMessageBox.critical(self, "Search Error", error)

    def on_download_clicked(self):
        selected_items = self.results_tree.selectedItems()
        if not selected_items:
            return
        
        to_download = []
        def add_recursive(item):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, dict): # It's a track candidate
                if data not in to_download:
                    to_download.append(data)
            else: # It's an artist or album node
                for i in range(item.childCount()):
                    add_recursive(item.child(i))

        for item in selected_items:
            add_recursive(item)
        
        if to_download:
            self.download_requested.emit(to_download)

class QueueTab(QWidget):
    def __init__(self, verbose_check: QCheckBox):
        super().__init__()
        self.verbose_check = verbose_check
        self.items: Dict[str, Dict[str, Any]] = {} # track_id -> widget info
        self.download_thread = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)
        
        header = QLabel("Download Queue")
        header.setFont(QFont(S_SANS, 20, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {S_BASE2}; margin-bottom: 10px;")
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"background-color: {S_BASE03}; border: none;")
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container_layout.setSpacing(12)
        self.container.setLayout(self.container_layout)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        self.setLayout(layout)

    def add_to_queue(self, items: List[Dict[str, Any]]):
        # items can be candidates or spotify track info
        for item in items:
            # For Spotify tracks, we need to search first. 
            # To keep the UI responsive, the DownloadThread will handle the search if 'id' is missing/different.
            track_id = item.get("id") or f"sp_{item.get('artist')}_{item.get('title')}"
            
            if track_id in self.items:
                continue

            row = QFrame()
            row.setObjectName("queueItemCard")
            row.setStyleSheet(f"""
                QFrame#queueItemCard {{ 
                    background-color: {S_BASE02}; 
                    border: 1px solid {S_BASE01};
                    border-radius: 8px; 
                }}
                QFrame#queueItemCard:hover {{
                    border-color: {S_BLUE};
                    background-color: #0a3e4d;
                }}
            """)
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(32, 20, 32, 20)
            row_layout.setSpacing(24)
            
            info_layout = QVBoxLayout()
            info_layout.setSpacing(4)
            name_label = QLabel(f"{item.get('artist', 'Unknown')} - {item.get('title', 'Unknown')}")
            name_label.setStyleSheet(f"color: {S_BASE2}; font-weight: 600; font-size: 14px;")
            status_label = QLabel("Pending")
            status_label.setStyleSheet(f"color: {S_BASE01}; font-family: {S_MONO}; font-size: 11px;")
            
            info_layout.addWidget(name_label)
            info_layout.addWidget(status_label)
            
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(0)
            progress.setFixedHeight(6)
            progress.setVisible(False) # Hide by default for pending
            
            row_layout.addLayout(info_layout, 3)
            row_layout.addWidget(progress, 2)
            
            rematch_btn = QPushButton("Rematch")
            rematch_btn.setObjectName("secondaryButton")
            rematch_btn.setFixedWidth(100)
            rematch_btn.setMinimumHeight(32)
            rematch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            rematch_btn.setVisible(False)
            rematch_btn.clicked.connect(lambda _, tid=track_id: self.on_rematch_clicked(tid))
            row_layout.addWidget(rematch_btn)
            
            row.setLayout(row_layout)
            self.container_layout.addWidget(row)
            
            self.items[track_id] = {
                "widget": row,
                "status_label": status_label,
                "progress": progress,
                "rematch_btn": rematch_btn,
                "data": item
            }

        if not self.download_thread or not self.download_thread.isRunning():
            self.start_next_batch()

    def on_rematch_clicked(self, track_id: str):
        item = self.items.get(track_id)
        if not item:
            return
            
        data = item["data"]
        query = f"{data.get('artist')} {data.get('title')}"
        
        dialog = RematchDialog(self, query, self.verbose_check.isChecked())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.get_selected_candidate()
            if selected:
                # Update item data and status
                item["data"] = selected
                item["status_label"].setText("Pending")
                item["status_label"].setStyleSheet(f"color: {S_BASE01};")
                item["progress"].setValue(0)
                item["rematch_btn"].setVisible(False)
                
                # If not already running, start the batch
                if not self.download_thread or not self.download_thread.isRunning():
                    self.start_next_batch()

    def start_next_batch(self):
        pending = [v["data"] for k, v in self.items.items() if v["status_label"].text() == "Pending"]
        if not pending:
            return
            
        self.download_thread = DownloadThread(pending, self.verbose_check.isChecked())
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.start()

    def update_progress(self, data: dict):
        track_id = data["id"]
        # If it was a spotify track, the ID might have changed to Deezer ID.
        # We need a better mapping, but for now let's try to find it.
        item = self.items.get(track_id)
        if not item:
            # Fallback: search by name if ID changed
            for k, v in self.items.items():
                if v["status_label"].text() == "Downloading" or v["status_label"].text() == "Pending":
                    item = v
                    break
        
        if item:
            item["status_label"].setText(data["status"])
            item["progress"].setValue(data["progress"])
            
            if data["status"] == "Completed":
                item["status_label"].setStyleSheet(f"color: {S_GREEN};")
                item["rematch_btn"].setVisible(True)
                item["rematch_btn"].setText("Rematch")
                item["progress"].setVisible(False)
            elif data["status"] == "Failed":
                item["status_label"].setStyleSheet(f"color: {S_RED};")
                item["rematch_btn"].setVisible(True)
                item["rematch_btn"].setText("Retry/Match")
                item["progress"].setVisible(False)
            elif data["status"] in ("Downloading", "Matching"):
                item["status_label"].setStyleSheet(f"color: {S_CYAN};")
                item["progress"].setVisible(True)

class ConfigTab(QWidget):
    def __init__(self):
        super().__init__()
        self.config_widgets = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header with Setup Wizard button
        header_layout = QHBoxLayout()
        header = QLabel("Settings")
        header.setFont(QFont(S_SANS, 18, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {S_BASE2};")
        
        setup_btn = QPushButton("Run Setup Wizard")
        setup_btn.setObjectName("secondaryButton")
        setup_btn.setMinimumHeight(36)
        setup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        setup_btn.clicked.connect(self.run_setup_wizard)
        
        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(setup_btn)
        layout.addLayout(header_layout)

        # Config Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"background-color: {S_BASE03}; border: 1px solid {S_BASE02}; border-radius: 8px;")
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(20, 20, 20, 20)
        self.scroll_layout.setSpacing(20)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        # Save button
        save_btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.setMinimumHeight(44)
        self.save_btn.setFixedWidth(200)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_config)
        save_btn_layout.addWidget(self.save_btn)
        save_btn_layout.addStretch()
        layout.addLayout(save_btn_layout)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"font-family: {S_MONO}; font-size: 11px;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        self.load_config_data()

    def load_config_data(self):
        # Clear existing widgets in scroll_layout
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        self.config_widgets = {}

        self.mdl_config, self.mdl_config_path = load_config_with_path()
        if self.mdl_config_path is None:
            self.mdl_config_path = str(_get_mdl_config_path())
        
        # Load streamrip defaults to merge
        try:
            streamrip_path = ensure_streamrip_config_exists()
            with open(streamrip_path, "r", encoding="utf-8") as f:
                streamrip_config = tomlkit.parse(f.read())
        except Exception:
            streamrip_config = {}

        # Merge
        full_config = dict(streamrip_config)
        if isinstance(self.mdl_config, dict):
            for section, values in self.mdl_config.items():
                if section in full_config and isinstance(values, dict) and isinstance(full_config[section], dict):
                    full_config[section].update(values)
                else:
                    full_config[section] = values

        for section_name, section in full_config.items():
            if isinstance(section, dict) and section:
                group = QGroupBox(section_name.upper())
                form = QFormLayout()
                form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
                form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
                form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
                form.setContentsMargins(20, 24, 20, 20)
                form.setSpacing(16)
                
                for key, value in section.items():
                    label = QLabel(key.replace("_", " ").title() + ":")
                    label.setMinimumWidth(140)
                    
                    tooltip = TOOLTIPS.get(key, "")
                    if tooltip:
                        label.setToolTip(tooltip)

                    if isinstance(value, bool):
                        widget = QCheckBox()
                        widget.setChecked(value)
                        widget.setCursor(Qt.CursorShape.PointingHandCursor)
                    elif isinstance(value, int):
                        widget = QSpinBox()
                        widget.setRange(-999999, 999999)
                        widget.setValue(value)
                        widget.setFixedWidth(100)
                    elif isinstance(value, (str, float)):
                        widget = QLineEdit()
                        widget.setText(str(value))
                        widget.setMinimumWidth(300)
                    else:
                        continue
                    
                    if tooltip:
                        widget.setToolTip(tooltip)
                        
                    form.addRow(label, widget)
                    self.config_widgets[(section_name, key)] = widget
                group.setLayout(form)
                self.scroll_layout.addWidget(group)
        
        self.scroll_layout.addStretch()

    def save_config(self):
        new_config = {}
        for (section, key), widget in self.config_widgets.items():
            if section not in new_config:
                new_config[section] = {}
            
            if isinstance(widget, QCheckBox):
                new_config[section][key] = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                new_config[section][key] = widget.value()
            elif isinstance(widget, QLineEdit):
                val = widget.text()
                try:
                    # Try to preserve floats if they look like floats
                    if "." in val:
                        new_config[section][key] = float(val)
                    else:
                        new_config[section][key] = val
                except ValueError:
                    new_config[section][key] = val
        
        try:
            Path(self.mdl_config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.mdl_config_path, "w", encoding="utf-8") as f:
                tomlkit.dump(new_config, f)
            self.status_label.setText("Configuration saved!")
            self.status_label.setStyleSheet(f"color: {S_GREEN};")
            # Reload to sync with streamrip if needed
            self.load_config_data()
        except Exception as e:
            self.status_label.setText(f"Error: {e}")
            self.status_label.setStyleSheet(f"color: {S_RED};")

    def run_setup_wizard(self):
        dialog = SetupWizardDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_config_data()

class LogRedirector(io.StringIO):
    """Redirects stdout to a Qt signal."""
    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def write(self, text):
        if text.strip():
            self.signal.emit(text.strip())

class MainWindow(QWidget):
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("music downloader")
        self.resize(1100, 800)
        
        # Setup logging redirection
        self.log_signal.connect(self.append_log)
        self.original_stdout = sys.stdout
        sys.stdout = LogRedirector(self.log_signal)
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title Bar
        title_bar = QFrame()
        title_bar.setFixedHeight(64)
        title_bar.setStyleSheet(f"background-color: {S_BASE02}; border-bottom: 1px solid {S_BASE01};")
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(24, 0, 24, 0)
        title_layout.setSpacing(16)
        
        title_label = QLabel("MUSIC DOWNLOADER")
        title_label.setFont(QFont(S_SANS, 14, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {S_BASE2}; letter-spacing: 1.5px;")
        
        try:
            v = get_version("music-downloader")
        except:
            v = "local"
        version_label = QLabel(f"v{v}")
        version_label.setStyleSheet(f"color: {S_BASE01}; font-family: {S_MONO}; font-weight: bold; font-size: 10px; margin-top: 6px;")
        
        self.verbose_check = QCheckBox("Verbose Logging")
        self.verbose_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.verbose_check.setStyleSheet(f"color: {S_BASE0}; font-size: 12px;")
        self.verbose_check.toggled.connect(self.toggle_console)
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(version_label, 0, Qt.AlignmentFlag.AlignBottom)
        title_layout.addStretch()
        title_layout.addWidget(self.verbose_check)
        title_bar.setLayout(title_layout)
        main_layout.addWidget(title_bar)

        # Central Splitter (Tabs + Console)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Tabs
        self.tabs = QTabWidget()
        self.search_tab = SearchTab(self.verbose_check)
        self.queue_tab = QueueTab(self.verbose_check)
        self.config_tab = ConfigTab()
        
        self.tabs.addTab(self.search_tab, "Search")
        self.tabs.addTab(self.queue_tab, "Queue")
        self.tabs.addTab(self.config_tab, "Settings")
        
        self.splitter.addWidget(self.tabs)
        
        # Console Log
        self.console_log = QTextEdit()
        self.console_log.setObjectName("consoleLog")
        self.console_log.setReadOnly(True)
        self.console_log.setPlaceholderText("Verbose logs will appear here...")
        self.console_log.setVisible(False)
        self.splitter.addWidget(self.console_log)
        
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(self.splitter)
        
        # Connect signals
        self.search_tab.download_requested.connect(self.on_download_requested)
        
        self.setLayout(main_layout)

    def toggle_console(self, checked):
        self.console_log.setVisible(checked)
        if checked:
            # Set initial sizes for splitter if not set
            if sum(self.splitter.sizes()) > 0 and self.splitter.sizes()[1] == 0:
                total_height = self.splitter.height()
                self.splitter.setSizes([int(total_height * 0.7), int(total_height * 0.3)])

    def append_log(self, text):
        self.console_log.append(text)
        # Auto-scroll to bottom
        self.console_log.verticalScrollBar().setValue(
            self.console_log.verticalScrollBar().maximum()
        )

    def closeEvent(self, event):
        # Restore stdout
        sys.stdout = self.original_stdout
        super().closeEvent(event)

    def on_download_requested(self, items: list):
        self.queue_tab.add_to_queue(items)
        self.tabs.setCurrentIndex(1) # Switch to Queue tab

def launch_gui():
    app = QApplication(sys.argv)
    app.setStyleSheet(get_stylesheet())
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
