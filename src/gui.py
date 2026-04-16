import sys
import io
import asyncio
import tomlkit
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QMessageBox,
    QTabWidget,
    QSpinBox,
    QTextEdit,
    QScrollArea,
    QGroupBox,
    QFormLayout,
)
from PyQt6.QtCore import QThread, pyqtSignal
from .spotify import is_spotify_link
from .core import process_spotify_link, download_track


async def run_download(query, verbose=False):
    """Run the download in asyncio"""
    old_stdout = sys.stdout
    captured_output = io.StringIO()
    sys.stdout = captured_output
    try:
        if is_spotify_link(query):
            await process_spotify_link(query, None, verbose)
        else:
            await download_track(query, None, verbose)
        output = captured_output.getvalue()
        return output or "Download completed successfully!"
    except Exception as e:
        output = captured_output.getvalue()
        return output + f"\nError: {str(e)}"
    finally:
        sys.stdout = old_stdout


def launch_gui():
    """Launch the GUI"""

    class DownloadThread(QThread):
        result_signal = pyqtSignal(str)
        progress_signal = pyqtSignal(str)

        def __init__(self, query, verbose):
            super().__init__()
            self.query = query
            self.verbose = verbose
            self.task = None
            self.loop = None

        def run(self):
            old_stdout = sys.stdout
            writer = SignalWriter(self.progress_signal)
            sys.stdout = writer

            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            try:
                if is_spotify_link(self.query):
                    coro = process_spotify_link(self.query, None, self.verbose)
                else:
                    coro = download_track(self.query, None, self.verbose)
                self.task = self.loop.create_task(coro)
                self.loop.run_until_complete(self.task)
                self.result_signal.emit("Download complete.")
            except asyncio.CancelledError:
                self.result_signal.emit("Download cancelled.")
            except Exception as e:
                self.result_signal.emit(f"Error: {str(e)}")
            finally:
                sys.stdout = old_stdout
                self.loop.close()

        def terminate(self):
            if self.loop and self.task and not self.task.done():
                self.loop.call_soon_threadsafe(self.task.cancel)
                self.loop.call_soon_threadsafe(self.loop.stop)

    class SignalWriter:
        """Replacement for sys.stdout that emits each printed line as a Qt signal."""

        def __init__(self, signal):
            self.signal = signal

        def write(self, text):
            if text.strip():
                self.signal.emit(text.rstrip("\n"))

        def flush(self):
            pass

    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("Music Downloader")
    window.setGeometry(100, 100, 800, 600)

    layout = QVBoxLayout()

    tabs = QTabWidget()

    # Download tab
    download_tab = QWidget()
    download_layout = QVBoxLayout()

    download_layout.addWidget(QLabel("Enter artist/song or Spotify link:"))
    query_input = QLineEdit()
    query_input.setPlaceholderText(
        "e.g., The Beatles - Hey Jude or https://open.spotify.com/track/..."
    )
    download_layout.addWidget(query_input)

    verbose_check = QCheckBox("Verbose output")
    download_layout.addWidget(verbose_check)

    download_btn = QPushButton("Download")
    download_layout.addWidget(download_btn)

    result_text = QTextEdit("")
    result_text.setReadOnly(True)
    result_text.setMaximumHeight(200)
    download_layout.addWidget(result_text)

    download_tab.setLayout(download_layout)
    tabs.addTab(download_tab, "Download")

    # Config tab
    config_tab = QWidget()
    config_layout = QVBoxLayout()

    scroll = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout()

    config_widgets = {}
    config = {}

    try:
        with open("mdl-config.toml", "r") as f:
            config = tomlkit.parse(f.read())
        for section_name, section in config.items():
            if isinstance(section, dict):
                group = QGroupBox(section_name.upper())
                form = QFormLayout()
                for key, value in section.items():
                    label = QLabel(key.replace("_", " ").title() + ":")
                    if isinstance(value, bool):
                        widget = QCheckBox()
                        widget.setChecked(value)
                    elif isinstance(value, int):
                        widget = QSpinBox()
                        widget.setRange(-999999, 999999)
                        widget.setValue(value)
                    elif isinstance(value, str):
                        widget = QLineEdit()
                        widget.setText(value)
                    else:
                        widget = QLineEdit()
                        widget.setText(str(value))
                    form.addRow(label, widget)
                    config_widgets[(section_name, key)] = widget
                group.setLayout(form)
                scroll_layout.addWidget(group)
    except Exception:
        scroll_layout.addWidget(QLabel("Config file not found or error loading"))

    scroll_widget.setLayout(scroll_layout)
    scroll.setWidget(scroll_widget)
    scroll.setWidgetResizable(True)
    config_layout.addWidget(scroll)

    save_btn = QPushButton("Save Config")
    config_layout.addWidget(save_btn)

    config_status = QLabel("")
    config_layout.addWidget(config_status)

    config_tab.setLayout(config_layout)
    tabs.addTab(config_tab, "Config")

    layout.addWidget(tabs)
    window.setLayout(layout)

    # Keep track of current thread
    current_thread = None

    def on_progress(text):
        result_text.append(text)
        result_text.verticalScrollBar().setValue(
            result_text.verticalScrollBar().maximum()
        )

    def download():
        nonlocal current_thread
        query = query_input.text().strip()
        if not query:
            QMessageBox.warning(window, "Error", "Please enter a query or Spotify link")
            return
        verbose = verbose_check.isChecked()
        result_text.clear()
        if current_thread and current_thread.isRunning():
            current_thread.terminate()
        current_thread = DownloadThread(query, verbose)
        current_thread.progress_signal.connect(on_progress)
        current_thread.result_signal.connect(on_progress)
        current_thread.start()

    download_btn.clicked.connect(download)

    def close_event(event):
        nonlocal current_thread
        if current_thread and current_thread.isRunning():
            current_thread.terminate()
            current_thread.wait(5000)  # Wait up to 5 seconds
        event.accept()

    window.closeEvent = close_event

    def save_config():
        for (section_name, key), widget in config_widgets.items():
            if section_name not in config:
                config[section_name] = {}
            original_value = config[section_name].get(key)
            if isinstance(original_value, bool):
                config[section_name][key] = widget.isChecked()
            elif isinstance(original_value, int):
                config[section_name][key] = widget.value()
            elif isinstance(original_value, str):
                config[section_name][key] = widget.text()
            else:
                config[section_name][key] = widget.text()
        try:
            with open("mdl-config.toml", "w") as f:
                tomlkit.dump(config, f)
            config_status.setText("Config saved!")
        except Exception as e:
            config_status.setText(f"Error saving config: {str(e)}")

    save_btn.clicked.connect(save_config)

    window.show()
    sys.exit(app.exec())
