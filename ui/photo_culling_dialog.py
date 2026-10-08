from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QObject, Slot
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton,
    QVBoxLayout,
)

from core.photo_intelligence import (
    analyse_folder, create_contact_sheet, write_analysis_report, write_library_json,
)


class CullingWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, folder, recursive):
        super().__init__()
        self.folder = folder
        self.recursive = recursive

    @Slot()
    def run(self):
        try:
            self.finished.emit(analyse_folder(self.folder, self.recursive))
        except Exception as exc:
            self.error.emit(str(exc))


class PhotoCullingDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.setWindowTitle("Photo Intelligence & Culling")
        self.resize(900, 700)
        self.folder = QLineEdit()
        self.recursive = QCheckBox("Include subfolders")
        self.recursive.setChecked(True)
        self.sort_mode = QComboBox()
        self.sort_mode.addItems(["Quality score", "Filename"])
        self.list = QListWidget()
        self.status = QLabel("Choose a photo folder and analyse it.")
        self.progress = QProgressBar()
        self.analyse_button = QPushButton("Analyse Photos")
        self.contact_button = QPushButton("Create Contact Sheet")
        self.report_button = QPushButton("Export CSV Report")
        self.rate_buttons = []
        for rating in range(6):
            button = QPushButton(str(rating))
            button.clicked.connect(lambda checked=False, r=rating: self.set_rating(r))
            self.rate_buttons.append(button)

        top = QHBoxLayout()
        top.addWidget(self.folder)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self.browse)
        top.addWidget(browse)
        top.addWidget(self.recursive)

        ratings = QHBoxLayout()
        ratings.addWidget(QLabel("Rating:"))
        for button in self.rate_buttons:
            ratings.addWidget(button)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.analyse_button)
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        layout.addWidget(self.list)
        layout.addLayout(ratings)
        layout.addWidget(self.contact_button)
        layout.addWidget(self.report_button)
        layout.addWidget(buttons)

        self.analyses = []
        self.library = {}
        self.thread = None
        self.worker = None
        self.analyse_button.clicked.connect(self.analyse)
        self.contact_button.clicked.connect(self.contact_sheet)
        self.report_button.clicked.connect(self.report)

    def browse(self):
        path = QFileDialog.getExistingDirectory(self, "Choose Photo Folder")
        if path:
            self.folder.setText(path)

    def analyse(self):
        folder = Path(self.folder.text().strip())
        if not folder.is_dir():
            QMessageBox.warning(self, "Photo Intelligence", "Choose a valid photo folder.")
            return
        self.analyse_button.setEnabled(False)
        self.list.clear()
        self.status.setText("Analysing photos...")
        self.thread = QThread(self)
        self.worker = CullingWorker(folder, self.recursive.isChecked())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.finished)
        self.worker.error.connect(lambda message: QMessageBox.critical(self, "Analysis failed", message))
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()

    @Slot(object)
    def finished(self, analyses):
        self.analyses = analyses
        self.analyse_button.setEnabled(True)
        self._load_library()
        self.refresh_list()
        self.status.setText(f"Analysed {len(analyses)} photos. Duplicate groups and quality scores are ready.")
        try:
            write_analysis_report(analyses, Path(self.folder.text()) / "PhotoEditor_analysis.csv")
            write_library_json(analyses, Path(self.folder.text()) / "PhotoEditor_library.json")
        except Exception:
            pass

    def _load_library(self):
        path = Path(self.folder.text()) / "PhotoEditor_library.json"
        if path.exists():
            try:
                self.library = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self.library = {}
        for analysis in self.analyses:
            self.library.setdefault(analysis.path, {}).setdefault("rating", 0)

    def refresh_list(self):
        mode = self.sort_mode.currentText()
        analyses = sorted(self.analyses, key=lambda a: (-a.quality_score, a.path.lower()) if mode == "Quality score" else a.path.lower())
        self.list.clear()
        for analysis in analyses:
            rating = int(self.library.get(analysis.path, {}).get("rating", 0))
            duplicate = f" | DUP {analysis.duplicate_group}" if analysis.duplicate_distance or sum(x.duplicate_group == analysis.duplicate_group for x in self.analyses) > 1 else ""
            item = QListWidgetItem(f"{rating}/5 | {analysis.quality_score:5.1f} | {Path(analysis.path).name}{duplicate}")
            item.setData(256, analysis.path)
            self.list.addItem(item)

    def set_rating(self, rating):
        item = self.list.currentItem()
        if not item:
            return
        path = item.data(256)
        self.library.setdefault(path, {})["rating"] = int(rating)
        self.refresh_list()
        self.list.setCurrentRow(max(0, self.list.currentRow()))

    def contact_sheet(self):
        if not self.analyses:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Contact Sheet", str(Path(self.folder.text()) / "contact_sheet.jpg"), "JPEG (*.jpg)")
        if path:
            create_contact_sheet(self.analyses, path)
            QMessageBox.information(self, "Contact Sheet", f"Created:\n{path}")

    def report(self):
        if not self.analyses:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Analysis Report", str(Path(self.folder.text()) / "PhotoEditor_analysis.csv"), "CSV (*.csv)")
        if path:
            write_analysis_report(self.analyses, path)
            write_library_json(self.analyses, Path(self.folder.text()) / "PhotoEditor_library.json")
            QMessageBox.information(self, "Report", f"Saved:\n{path}")
