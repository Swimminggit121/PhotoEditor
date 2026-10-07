from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from processing.audio_library import (
    GENRES,
    download_cc0,
    get_api_token,
    search_cc0,
    set_api_token,
)


class _LibraryWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, work, parent=None):
        super().__init__(parent)
        self.work = work

    def run(self):
        try:
            self.completed.emit(self.work())
        except Exception as exc:
            self.failed.emit(str(exc))


class AudioLibraryDialog(QDialog):
    audio_added = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Licensed Audio Library")
        self.resize(850, 560)
        self._results = []
        self._worker = None

        self.genre = QComboBox()
        self.genre.addItems(GENRES)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search music, ambience, foley, or sound effects")
        self.search_button = QPushButton("Search")
        self.key_button = QPushButton("Freesound API key…")
        header = QHBoxLayout()
        header.addWidget(self.genre)
        header.addWidget(self.search, 1)
        header.addWidget(self.search_button)
        header.addWidget(self.key_button)

        self.results = QTableWidget(0, 4)
        self.results.setHorizontalHeaderLabels(["Sound", "Creator", "Downloads", "Duration"])
        self.results.setSelectionBehavior(QTableWidget.SelectRows)
        self.results.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results.horizontalHeader().setStretchLastSection(True)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.note = QLabel(
            "Searches Freesound’s public catalog and only offers CC0 1.0 tracks for download. "
            "“Popular” is sorted by downloads, not a music chart. Source and license notes are saved beside each file."
        )
        self.note.setWordWrap(True)
        self.download_button = QPushButton("Download selected CC0 audio")
        self.preview_button = QPushButton("Play preview")
        self.preview_button.clicked.connect(self.preview_selected)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.results, 1)
        layout.addWidget(self.note)
        footer = QHBoxLayout()
        footer.addWidget(self.preview_button)
        footer.addWidget(self.download_button)
        footer.addStretch(1)
        footer.addWidget(self.buttons)
        layout.addLayout(footer)

        self.search_button.clicked.connect(self.search_catalog)
        self.search.returnPressed.connect(self.search_catalog)
        self.genre.currentTextChanged.connect(self._fill_query)
        self.key_button.clicked.connect(self.configure_key)
        self.download_button.clicked.connect(self.download_selected)
        self.results.itemDoubleClicked.connect(lambda _item: self.download_selected())

    def _fill_query(self, genre):
        suggestion = GENRES.get(genre, "")
        if suggestion and (not self.search.text().strip() or self.search.text().strip() in GENRES.values()):
            self.search.setText(suggestion)

    def configure_key(self):
        current = get_api_token()
        token, ok = QInputDialog.getText(
            self,
            "Freesound API key",
            "Personal API key (stored in the Windows credential store):",
            QLineEdit.Password,
            current,
        )
        if not ok:
            return
        try:
            set_api_token(token)
            self.note.setText(
                "API key stored in the Windows credential store. The catalog is limited to CC0 1.0 downloads; "
                "non-CC0 tracks are not offered."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Could not store API key", str(exc))

    def _start(self, work, success_message):
        if self._worker and self._worker.isRunning():
            return
        self.search_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.note.setText("Contacting Freesound…")
        self._worker = _LibraryWorker(work, self)
        self._worker.completed.connect(success_message)
        self._worker.failed.connect(self._failed)
        self._worker.finished.connect(self._finished)
        self._worker.start()

    def _finished(self):
        self.search_button.setEnabled(True)
        self.download_button.setEnabled(True)

    def _failed(self, message):
        QMessageBox.critical(self, "Audio library error", message)
        self.note.setText("Search or download failed. Review the message, then try again.")

    def search_catalog(self):
        term = self.search.text().strip() or GENRES.get(self.genre.currentText(), "music")
        self.search.setText(term)

        def done(items):
            self._results = items
            self.results.setRowCount(len(items))
            for row, sound in enumerate(items):
                values = (
                    str(sound.get("name", "Untitled")),
                    str(sound.get("username", "Unknown")),
                    str(sound.get("downloads", 0)),
                    f"{float(sound.get('duration', 0)):.1f}s",
                )
                for column, value in enumerate(values):
                    cell = QTableWidgetItem(value)
                    cell.setData(Qt.UserRole, row)
                    self.results.setItem(row, column, cell)
            self.results.resizeColumnsToContents()
            self.note.setText(
                f"{len(items)} CC0 1.0 results for “{term}”, ordered by download count. "
                "Every downloaded file includes its source and license record."
            )

        self._start(lambda: search_cc0(term), done)

    def download_selected(self):
        row = self.results.currentRow()
        if row < 0 or row >= len(self._results):
            QMessageBox.information(self, "Choose a sound", "Select a search result first.")
            return
        sound = dict(self._results[row])
        destination = Path.home() / "Music" / "PhotoEditor Audio Library"
        self._start(
            lambda: download_cc0(sound, destination),
            lambda path: self._downloaded(path),
        )

    def preview_selected(self):
        row = self.results.currentRow()
        if row < 0 or row >= len(self._results):
            QMessageBox.information(self, "Choose a sound", "Select a search result first.")
            return
        previews = self._results[row].get("previews", {})
        url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
        if not url:
            QMessageBox.information(self, "Preview unavailable", "This result has no playable audio preview.")
            return
        self.player.setSource(QUrl(url))
        self.player.play()

    def _downloaded(self, path):
        self.note.setText(f"Downloaded with CC0 source/license notes: {path}")
        self.audio_added.emit(str(path))

    def closeEvent(self, event):
        self.player.stop()
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "Audio request in progress", "Wait for the current catalog request to finish before closing.")
            event.ignore()
            return
        event.accept()
