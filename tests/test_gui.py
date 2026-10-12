import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import stat
import tomlkit
import pytest
from PyQt6.QtWidgets import QApplication, QLineEdit
from src.gui import MainWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def window(app, tmp_path):
    path = tmp_path / "mdl-config.toml"
    path.write_text(
        '# preserved\n[deezer]\narl = "secret"\nquality = 1\n[metadata]\nexclude = ["title"]\n[custom]\nvalue = "keep"\n'
    )
    widget = MainWindow(config_path=path)
    yield widget, path
    widget.close()


def candidate(identifier="1", artist="Artist", album="Album"):
    return {
        "id": identifier,
        "artist": artist,
        "album": album,
        "title": "Track",
        "track": {"id": identifier, "album": {"id": "2"}},
    }


def test_grouped_results_and_queue_selection(window):
    widget, _ = window
    widget.show_candidates([candidate(), candidate("3")])
    assert widget.results.topLevelItemCount() == 1
    album = widget.results.topLevelItem(0).child(0)
    assert album.childCount() == 2
    widget.results.setCurrentItem(album.child(1))
    widget.queue_selected()
    assert widget.queue_items[0]["candidate"]["id"] == "3"
    assert widget.queue_table.rowCount() == 1


def test_config_save_preserves_lists_comments_and_external_edits(window):
    widget, path = window
    doc = tomlkit.parse(path.read_text())
    doc["custom"]["value"] = "external"
    path.write_text(tomlkit.dumps(doc))
    field = widget.config_widgets[("deezer", "quality")]
    field.setValue(2)
    widget.save_config()
    saved = tomlkit.parse(path.read_text())
    assert saved["metadata"]["exclude"] == ["title"]
    assert saved["custom"]["value"] == "external"
    assert saved["deezer"]["quality"] == 2
    assert "# preserved" in path.read_text()
    assert (
        widget.config_widgets[("deezer", "arl")].echoMode()
        == QLineEdit.EchoMode.Password
    )
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_invalid_array_does_not_write(window):
    widget, path = window
    before = path.read_bytes()
    widget.config_widgets[("metadata", "exclude")].setText("invalid [")
    widget.save_config()
    assert path.read_bytes() == before
    assert "Error" in widget.config_status.text()


def test_group_selection_deduplicates_queue_and_formats_metadata(window):
    widget, _ = window
    first = candidate()
    first.update(duration=123, explicit=True)
    widget.show_candidates([first, candidate("3")])
    artist = widget.results.topLevelItem(0)
    artist.setSelected(True)
    artist.child(0).child(0).setSelected(True)
    widget.queue_selected()
    widget.queue_selected()
    assert [item["candidate"]["id"] for item in widget.queue_items] == ["1", "3"]
    assert artist.child(0).child(0).text(1) == "2:03"
    assert artist.child(0).child(0).text(2) == "Yes"


def test_retry_resets_selected_queue_item(window):
    widget, _ = window
    widget.show_candidates([candidate()])
    widget.results.topLevelItem(0).setSelected(True)
    widget.queue_selected()
    widget.queue_items[0]["status"] = "Failed"
    widget.queue_table.selectRow(0)
    widget.retry_selected()
    assert widget.queue_items[0]["status"] == "Pending"
    assert widget.config_widgets[("deezer", "quality")].toolTip()


def test_replace_queue_match_updates_identity_and_status(window):
    widget, _ = window
    widget.show_candidates([candidate()])
    widget.results.topLevelItem(0).setSelected(True)
    widget.queue_selected()
    widget.queue_items[0]["status"] = "Failed"
    widget.replace_queue_candidate(0, candidate("7", album="Rematch"))
    assert widget.queue_items[0]["candidate"]["id"] == "7"
    assert widget.queue_items[0]["status"] == "Pending"
    assert "Rematch" in widget.queue_table.item(0, 0).text()


def test_gui_config_picker_and_worker_share_queue_options(window, monkeypatch):
    from src.gui import Worker
    from unittest.mock import AsyncMock
    import asyncio
    from src.workflow import DownloadOutcome

    widget, _ = window
    monkeypatch.setattr(
        "src.gui.QFileDialog.getOpenFileName", lambda *args: ("/custom/engine.toml", "")
    )
    widget.choose_engine_config()
    assert widget.engine_config_path == "/custom/engine.toml"
    queue = AsyncMock(return_value=[DownloadOutcome("query", "skipped", "Duplicate")])
    monkeypatch.setattr("src.gui.run_queue", queue)
    worker = Worker(
        "download",
        "query",
        candidate=candidate(),
        engine_config_path=widget.engine_config_path,
        retries=2,
    )
    assert asyncio.run(worker.execute()) is True
    assert queue.call_args.kwargs["config_path"] == "/custom/engine.toml"
    assert queue.call_args.kwargs["retries"] == 2


def test_gui_batch_keeps_all_outcomes(window):
    widget, _ = window
    widget.show_candidates([candidate()])
    widget.results.topLevelItem(0).setSelected(True)
    widget.queue_selected()
    widget.active_row = 0
    widget.record_outcome({"status": "failed", "query": "first"})
    widget.record_outcome({"status": "downloaded", "query": "second"})
    assert widget.queue_items[0]["status"] == "failed"
    assert len(widget.queue_items[0]["outcomes"]) == 2
