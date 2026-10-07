from __future__ import annotations

from pathlib import Path

from PIL.ImageQt import ImageQt
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QPixmap, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.batch_processor import BatchProcessor
from core.photo_catalog import PhotoCatalog, PhotoRecord
from image.loader import load_preview
from ui.export_dialog import ExportDialog


class _CatalogWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int, str)

    def __init__(self, catalog: PhotoCatalog, shoot_id: str, recursive: bool, parent=None):
        super().__init__(parent)
        self.catalog = catalog
        self.shoot_id = shoot_id
        self.recursive = recursive

    def run(self):
        try:
            result = self.catalog.index_shoot(
                self.shoot_id,
                recursive=self.recursive,
                progress=lambda current, total, path: self.progress.emit(current, total, path.name),
            )
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class _ExportWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int, str)

    def __init__(self, input_root, output_root, paths, recipe, auto_edit, parent=None):
        super().__init__(parent)
        self.input_root = Path(input_root)
        self.output_root = Path(output_root)
        self.paths = paths
        self.recipe = recipe
        self.auto_edit = auto_edit

    def run(self):
        try:
            processor = BatchProcessor(
                self.input_root,
                self.output_root,
                mode="professional" if self.auto_edit else "original",
                recursive=True,
                recipe=self.recipe,
                input_files=self.paths,
            )
            result = processor.run(
                lambda current, total, path: self.progress.emit(current, total, path.name)
            )
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class _PreviewWorker(QThread):
    ready = Signal(int, object, str)

    def __init__(self, photo_id: int, path: Path, generation: int, parent=None):
        super().__init__(parent)
        self.photo_id = photo_id
        self.path = path
        self.generation = generation

    def run(self):
        try:
            image = load_preview(self.path, max_dimension=1100)
            self.ready.emit(self.generation, ImageQt(image).copy(), "")
        except Exception as exc:
            self.ready.emit(self.generation, None, str(exc))


class PhotoCatalogWindow(QMainWindow):
    photo_selected = Signal(str)
    photo_workspace_requested = Signal()
    video_requested = Signal(object)
    PAGE_SIZE = 500

    def __init__(self, parent=None, catalog: PhotoCatalog | None = None):
        super().__init__(parent)
        self.catalog = catalog or PhotoCatalog()
        self.setWindowTitle("PhotoEditor — Photo Catalog")
        self.setMinimumSize(1050, 650)
        self.resize(1500, 900)
        self._records: list[PhotoRecord] = []
        self._worker: QThread | None = None
        self._preview_workers: set[_PreviewWorker] = set()
        self._preview_generation = 0
        self._preview_pixmap = QPixmap()
        self._busy = False

        heading = QLabel("Photo Catalog")
        heading.setStyleSheet("font-size: 20pt; font-weight: 600;")
        self.subtitle = QLabel(
            "Search and review shoots without moving originals. Ratings and culling notes stay in the local catalog."
        )
        self.subtitle.setWordWrap(True)

        self.shoot_picker = QComboBox()
        self.shoot_picker.setMinimumWidth(240)
        self.shoot_picker.currentIndexChanged.connect(self.refresh_photos)
        self.add_shoot_button = QPushButton("Add photo folder…")
        self.index_button = QPushButton("Scan for changes")
        self.relink_button = QPushButton("Relink missing shoot…")
        self.backup_button = QPushButton("Back up catalog…")
        self.restore_button = QPushButton("Restore catalog…")
        self.add_shoot_button.clicked.connect(self.add_shoot)
        self.index_button.clicked.connect(self.index_current_shoot)
        self.relink_button.clicked.connect(self.relink_shoot)
        self.backup_button.clicked.connect(self.backup_catalog)
        self.restore_button.clicked.connect(self.restore_catalog)

        shoot_row = QHBoxLayout()
        shoot_row.addWidget(QLabel("Shoot"))
        shoot_row.addWidget(self.shoot_picker, 1)
        for button in (self.add_shoot_button, self.index_button, self.relink_button):
            shoot_row.addWidget(button)
        backup_row = QHBoxLayout()
        backup_row.addStretch(1)
        backup_row.addWidget(self.backup_button)
        backup_row.addWidget(self.restore_button)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search filenames, dates, camera, lens, keywords, and review hints")
        self.search.textChanged.connect(self.refresh_photos)
        self.status_filter = QComboBox()
        self.status_filter.addItem("All review states", "all")
        self.status_filter.addItem("Unreviewed", "unreviewed")
        self.status_filter.addItem("Picks", "pick")
        self.status_filter.addItem("Rejected · review only", "reject")
        self.status_filter.currentIndexChanged.connect(self.refresh_photos)
        self.sort_picker = QComboBox()
        self.sort_picker.addItem("Newest capture", "newest")
        self.sort_picker.addItem("Highest quality cue", "quality")
        self.sort_picker.addItem("Review warnings first", "warnings")
        self.sort_picker.addItem("Highest rating", "rating")
        self.sort_picker.currentIndexChanged.connect(self.refresh_photos)
        self.issues_only = QCheckBox("Needs attention")
        self.issues_only.toggled.connect(self.refresh_photos)
        filter_row = QHBoxLayout()
        filter_row.addWidget(self.search, 1)
        filter_row.addWidget(self.status_filter)
        filter_row.addWidget(self.sort_picker)
        filter_row.addWidget(self.issues_only)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Rating", "Review", "Photo", "Captured", "Camera / lens", "Quality cue*", "Review hints"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 75)
        self.table.setColumnWidth(1, 125)
        self.table.setColumnWidth(2, 250)
        self.table.setColumnWidth(3, 155)
        self.table.setColumnWidth(4, 220)
        self.table.setColumnWidth(5, 95)
        self.table.setMinimumWidth(580)
        self.table.itemSelectionChanged.connect(self.show_selected_preview)
        self.table.cellDoubleClicked.connect(lambda *_: self.open_selected())
        self.load_more_button = QPushButton("Load next 500 photos")
        self.load_more_button.clicked.connect(self.load_more_photos)

        self.preview = QLabel("Select a photo to inspect it.")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(320, 280)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.preview.setFixedHeight(360)
        self.preview.setStyleSheet("background: #101010; border: 1px solid #343434;")
        self.photo_title = QLabel("No photo selected")
        self.photo_title.setWordWrap(True)
        self.photo_metadata = QLabel("")
        self.photo_metadata.setWordWrap(True)
        self.quality_summary = QLabel(
            "Quality cue estimates focus and exposure only. It is a local heuristic, not a verdict."
        )
        self.quality_summary.setWordWrap(True)
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("Add comma-separated keywords")
        self.keyword_edit.editingFinished.connect(self.save_keywords)

        self.pick_button = QPushButton("Mark pick")
        self.review_button = QPushButton("Needs review")
        self.reject_button = QPushButton("Flag reject")
        self.clear_rating_button = QPushButton("Clear rating")
        self.open_button = QPushButton("Open in Photo Editor")
        self.workspace_button = QPushButton("Open Photo Editor")
        self.video_button = QPushButton("Create video from selected…")
        self.export_button = QPushButton("Export selected…")
        self.pick_button.clicked.connect(lambda: self.set_selected_status("pick"))
        self.review_button.clicked.connect(lambda: self.set_selected_status("unreviewed"))
        self.reject_button.clicked.connect(lambda: self.set_selected_status("reject"))
        self.clear_rating_button.clicked.connect(lambda: self.rate_selected(0))
        self.open_button.clicked.connect(self.open_selected)
        self.workspace_button.clicked.connect(self.open_photo_workspace)
        self.video_button.clicked.connect(self.create_video_from_selected)
        self.export_button.clicked.connect(self.export_selected)

        review_actions = QHBoxLayout()
        review_actions.addWidget(self.pick_button)
        review_actions.addWidget(self.review_button)
        review_actions.addWidget(self.reject_button)
        review_actions.addWidget(self.clear_rating_button)
        detail_layout = QVBoxLayout()
        detail_layout.addWidget(self.photo_title)
        detail_layout.addWidget(self.preview, 1)
        detail_layout.addWidget(self.photo_metadata)
        detail_layout.addWidget(self.quality_summary)
        detail_layout.addWidget(QLabel("Keywords"))
        detail_layout.addWidget(self.keyword_edit)
        detail_layout.addLayout(review_actions)
        detail_layout.addWidget(self.open_button)
        detail_layout.addWidget(self.workspace_button)
        detail_layout.addWidget(self.video_button)
        detail_layout.addWidget(self.export_button)
        detail_layout.addStretch(1)
        detail = QWidget()
        detail.setLayout(detail_layout)
        detail.setMinimumWidth(340)
        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QScrollArea.NoFrame)
        self.detail_scroll.setWidget(detail)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(self.detail_scroll)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self.job_status = QLabel("Catalog is local; photos stay in their source folders.")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.addWidget(heading)
        layout.addWidget(self.subtitle)
        layout.addLayout(shoot_row)
        layout.addLayout(backup_row)
        layout.addLayout(filter_row)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.load_more_button, 0, Qt.AlignHCenter)
        layout.addWidget(self.job_status)
        layout.addWidget(self.progress)
        self.setCentralWidget(root)

        for index in range(1, 6):
            shortcut = QShortcut(QKeySequence(str(index)), self.table)
            shortcut.activated.connect(lambda value=index: self.rate_selected(value))
        self._refresh_shoots()
        self.load_more_button.hide()
        self._set_selection_actions(False)

    def _selected_shoot_id(self) -> str | None:
        return self.shoot_picker.currentData()

    def _selected_records(self) -> list[PhotoRecord]:
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        records = []
        for row in rows:
            item = self.table.item(row, 0)
            if item is None:
                continue
            photo_id = item.data(Qt.UserRole)
            record = next((entry for entry in self._records if entry.id == photo_id), None)
            if record is not None:
                records.append(record)
        return records

    def _refresh_shoots(self, selected_id: str | None = None):
        selected_id = selected_id or self._selected_shoot_id()
        shoots = self.catalog.shoots()
        self.shoot_picker.blockSignals(True)
        self.shoot_picker.clear()
        for shoot in shoots:
            label = f"{shoot['name']} · {shoot['photo_count']}"
            if shoot["missing_count"]:
                label += f" · {shoot['missing_count']} missing"
            self.shoot_picker.addItem(label, shoot["id"])
        index = self.shoot_picker.findData(selected_id) if selected_id else -1
        if index >= 0:
            self.shoot_picker.setCurrentIndex(index)
        self.shoot_picker.blockSignals(False)
        self.refresh_photos()

    def add_shoot(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose a shoot's originals folder")
        if not folder:
            return
        try:
            shoot_id = self.catalog.add_shoot(folder)
            self._refresh_shoots(shoot_id)
            self.index_current_shoot()
        except Exception as exc:
            QMessageBox.critical(self, "Could not add shoot", str(exc))

    def index_current_shoot(self):
        shoot_id = self._selected_shoot_id()
        if not shoot_id:
            QMessageBox.information(self, "Scan shoot", "Add a photo folder before scanning.")
            return
        if self._busy:
            return
        self._busy = True
        self._set_job_busy(True)
        self.progress.setRange(0, 0)
        self.progress.show()
        self.job_status.setText("Reading photo metadata and calculating local focus/exposure review hints…")
        worker = _CatalogWorker(self.catalog, shoot_id, recursive=True, parent=self)
        self._worker = worker
        worker.progress.connect(self._scan_progress)
        worker.completed.connect(self._scan_completed)
        worker.failed.connect(self._scan_failed)
        worker.start()

    def _scan_progress(self, current, total, name):
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(current)
        self.job_status.setText(f"Indexing {current}/{total}: {name}")

    def _scan_completed(self, result):
        self._busy = False
        self._set_job_busy(False)
        self._refresh_shoots(self._selected_shoot_id())
        text = (
            f"Indexed {result.indexed} files; found {result.duplicate_groups} visual duplicate group(s). "
            "Recommendations do not move or delete files."
        )
        if result.errors:
            text += f" {len(result.errors)} item(s) need attention."
            details = "\n".join(f"{path.name}: {message}" for path, message in result.errors[:20])
            self.job_status.setToolTip(details)
            QMessageBox.warning(self, "Some photos could not be indexed", text + "\n\n" + details)
        else:
            self.job_status.setToolTip("")
        self.job_status.setText(text)

    def _scan_failed(self, message):
        self._busy = False
        self._set_job_busy(False)
        self._refresh_shoots(self._selected_shoot_id())
        self.job_status.setText("Shoot scan did not finish.")
        QMessageBox.critical(self, "Could not scan shoot", message)

    def _set_job_busy(self, busy):
        self.progress.setVisible(busy)
        for button in (
            self.add_shoot_button, self.index_button, self.relink_button,
            self.backup_button, self.restore_button,
        ):
            button.setEnabled(not busy)
        self.shoot_picker.setEnabled(not busy)
        self.search.setEnabled(not busy)
        self.status_filter.setEnabled(not busy)
        self.issues_only.setEnabled(not busy)
        self.sort_picker.setEnabled(not busy)
        self.table.setEnabled(not busy)
        self._set_selection_actions(bool(self._selected_records()))

    def refresh_photos(self, *_):
        shoot_id = self._selected_shoot_id()
        self.table.setRowCount(0)
        self._records = []
        if not shoot_id:
            self.subtitle.setText("Add an originals folder to create your first shoot catalog.")
            self.preview.clear()
            self.preview.setText("Select a photo to inspect it.")
            self._preview_pixmap = QPixmap()
            self._set_selection_actions(False)
            self.load_more_button.hide()
            return
        shoot = self.catalog.shoot(shoot_id)
        self.subtitle.setText(
            f"{shoot['root_path']} · originals are referenced in place; catalog records and flags are stored locally."
        )
        self._records = self.catalog.photos(
            shoot_id,
            query=self.search.text(),
            status=self.status_filter.currentData(),
            issues_only=self.issues_only.isChecked(),
            sort=self.sort_picker.currentData(),
            limit=self.PAGE_SIZE,
            offset=0,
        )
        self.table.setRowCount(len(self._records))
        self._populate_rows(0)
        self.load_more_button.setVisible(len(self._records) == self.PAGE_SIZE)
        if not self._records:
            self.job_status.setText("No photos match this shoot and filter.")
            self._preview_pixmap = QPixmap()
            self.preview.setPixmap(self._preview_pixmap)
            self.preview.setText("No matching photos.")
            self.photo_title.setText("No photo selected")
            self.photo_metadata.clear()
            self.quality_summary.setText(
                "Focus and exposure hints are local heuristics for review, not a verdict on image quality."
            )
            self.keyword_edit.clear()
        self._set_selection_actions(False)

    def _populate_rows(self, start):
        for row in range(start, len(self._records)):
            record = self._records[row]
            values = (
                f"{'★' * record.rating}{'☆' * (5 - record.rating)}",
                {
                    "unreviewed": "Unreviewed",
                    "pick": "Pick",
                    "reject": "Reject · flagged",
                }[record.status],
                record.name + (" · MISSING" if record.missing else ""),
                record.captured_at,
                " · ".join(value for value in (record.camera, record.lens) if value),
                f"{record.quality_score:.1f}" if record.quality_score is not None else "",
                "; ".join(
                    value for value in (
                        record.quality_notes,
                        "visual duplicate candidate" if record.duplicate_group else "",
                    ) if value
                ),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, record.id)
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)

    def load_more_photos(self):
        shoot_id = self._selected_shoot_id()
        if not shoot_id:
            return
        start = len(self._records)
        more = self.catalog.photos(
            shoot_id,
            query=self.search.text(),
            status=self.status_filter.currentData(),
            issues_only=self.issues_only.isChecked(),
            sort=self.sort_picker.currentData(),
            limit=self.PAGE_SIZE,
            offset=start,
        )
        self._records.extend(more)
        old_row_count = self.table.rowCount()
        self.table.setRowCount(old_row_count + len(more))
        self._populate_rows(old_row_count)
        self.load_more_button.setVisible(len(more) == self.PAGE_SIZE)

    def show_selected_preview(self):
        records = self._selected_records()
        if not records:
            self._set_selection_actions(False)
            return
        record = records[0]
        self._set_selection_actions(True)
        self.photo_title.setText(record.name)
        self.photo_metadata.setText(
            f"{record.width} × {record.height} · {record.file_size / (1024 * 1024):.1f} MB\n"
            f"Captured: {record.captured_at or 'not recorded'}\n"
            f"Camera: {record.camera or 'not recorded'}\nLens: {record.lens or 'not recorded'}"
        )
        self.quality_summary.setText(
            "Local review hints: "
            + (record.quality_notes or "no focus or exposure warning detected")
            + (f"; possible visual duplicate group ({record.duplicate_group[:8]})" if record.duplicate_group else "")
            + "\nThese estimates can be wrong; inspect the original before deciding."
        )
        self.keyword_edit.setText(record.keywords)
        if record.missing or not record.path.is_file():
            self._preview_pixmap = QPixmap()
            self.preview.setPixmap(self._preview_pixmap)
            self.preview.setText("Original file is missing; relink this shoot folder.")
            return
        self._preview_generation += 1
        self.preview.setText("Loading source preview…")
        worker = _PreviewWorker(record.id, record.path, self._preview_generation, self)
        self._preview_workers.add(worker)
        worker.ready.connect(self._preview_ready)
        worker.finished.connect(lambda worker=worker: self._preview_workers.discard(worker))
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _preview_ready(self, generation, image, error):
        if generation != self._preview_generation:
            return
        if image is None:
            self._preview_pixmap = QPixmap()
            self.preview.setPixmap(self._preview_pixmap)
            self.preview.setText(f"Preview unavailable: {error}")
        else:
            self.preview.setText("")
            self._preview_pixmap = QPixmap.fromImage(image)
            self._scale_preview()

    def _scale_preview(self):
        if self._preview_pixmap.isNull():
            return
        self.preview.setPixmap(
            self._preview_pixmap.scaled(
                self.preview.contentsRect().size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._scale_preview()

    def _set_selection_actions(self, enabled):
        records = self._selected_records()
        for button in (
            self.pick_button, self.review_button, self.reject_button,
            self.clear_rating_button, self.open_button, self.video_button, self.export_button,
        ):
            button.setEnabled(enabled and not self._busy)
        self.workspace_button.setEnabled(not self._busy)
        self.keyword_edit.setEnabled(len(records) == 1 and not self._busy)

    def set_selected_status(self, status):
        records = self._selected_records()
        if not records:
            return
        for record in records:
            self.catalog.update_photo(record.id, status=status)
        self.refresh_photos()

    def rate_selected(self, rating):
        for record in self._selected_records():
            self.catalog.update_photo(record.id, rating=rating)
        self.refresh_photos()

    def save_keywords(self):
        records = self._selected_records()
        if len(records) != 1:
            return
        self.catalog.update_photo(records[0].id, keywords=self.keyword_edit.text())
        self.refresh_photos()

    def open_selected(self):
        records = self._selected_records()
        if not records:
            QMessageBox.information(self, "Open in Photo Editor", "Select one photo first.")
            return
        if len(records) != 1:
            QMessageBox.information(self, "Open in Photo Editor", "Select exactly one photo to open.")
            return
        record = records[0]
        if record.missing or not record.path.is_file():
            QMessageBox.warning(self, "Original missing", "Relink the shoot folder before opening this photo.")
            return
        self.photo_selected.emit(str(record.path))

    def open_photo_workspace(self):
        self.photo_workspace_requested.emit()

    def create_video_from_selected(self):
        records = self._selected_records()
        if not records:
            QMessageBox.information(self, "Create photo video", "Select one or more finished photos first.")
            return
        missing = [record.name for record in records if record.missing or not record.path.is_file()]
        if missing:
            QMessageBox.warning(
                self, "Originals missing",
                "Relink the shoot before creating a video:\n" + "\n".join(missing[:10]),
            )
            return
        self.video_requested.emit([str(record.path) for record in records])

    def relink_shoot(self):
        shoot_id = self._selected_shoot_id()
        if not shoot_id:
            return
        folder = QFileDialog.getExistingDirectory(self, "Choose the moved shoot's new originals folder")
        if not folder:
            return
        try:
            self.catalog.relink_shoot(shoot_id, folder)
            self._refresh_shoots(shoot_id)
            self.index_current_shoot()
        except Exception as exc:
            QMessageBox.critical(self, "Could not relink shoot", str(exc))

    def backup_catalog(self):
        default = self.catalog.path.with_name("PhotoEditor-catalog-backup.sqlite3")
        target, _ = QFileDialog.getSaveFileName(
            self, "Back up photo catalog", str(default), "SQLite backup (*.sqlite3)"
        )
        if not target:
            return
        try:
            saved = self.catalog.backup(target)
            self.job_status.setText(f"Catalog backup saved: {saved}")
        except Exception as exc:
            QMessageBox.critical(self, "Could not back up catalog", str(exc))

    def restore_catalog(self):
        source, _ = QFileDialog.getOpenFileName(
            self, "Restore photo catalog", "", "SQLite backup (*.sqlite3 *.db)"
        )
        if not source:
            return
        answer = QMessageBox.warning(
            self,
            "Replace current catalog?",
            "Restoring replaces the current catalog database and review metadata. "
            "Original photo files are not changed. Back up the current catalog first if you need it.",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self.catalog.restore(source)
            self._refresh_shoots()
            self.job_status.setText("Catalog and review metadata restored. Original files were not changed.")
        except Exception as exc:
            QMessageBox.critical(self, "Could not restore catalog", str(exc))

    def export_selected(self):
        records = self._selected_records()
        if not records:
            QMessageBox.information(self, "Export selected", "Select one or more photos first.")
            return
        missing = [record.name for record in records if record.missing or not record.path.is_file()]
        if missing:
            QMessageBox.warning(
                self, "Originals missing",
                "Relink the shoot before exporting these photos:\n" + "\n".join(missing[:10]),
            )
            return
        shoot = self.catalog.shoot(records[0].shoot_id)
        input_root = Path(shoot["root_path"]).resolve()
        default_output = input_root.parent / f"{input_root.name}_Edited"
        output_root = default_output.resolve()
        if output_root == input_root or input_root in output_root.parents:
            QMessageBox.warning(
                self,
                "Choose a separate folder",
                "The default edited-copies folder is inside the originals folder. "
                "Move the originals into their own folder or use Professional Batch Edit to choose another destination.",
            )
            return
        settings = ExportDialog(self, batch_mode=True)
        if settings.exec() != ExportDialog.Accepted:
            return
        try:
            recipe = settings.current_recipe()
        except ValueError as exc:
            QMessageBox.warning(self, "Check export settings", str(exc))
            return
        self._busy = True
        self._set_job_busy(True)
        self.progress.setRange(0, len(records))
        self.progress.setValue(0)
        self.job_status.setText(
            f"Preparing {len(records)} edited copies in {output_root}… originals will remain untouched."
        )
        worker = _ExportWorker(
            input_root,
            output_root,
            [record.path for record in records],
            recipe,
            settings.auto_edit.isChecked(),
            self,
        )
        self._worker = worker
        worker.progress.connect(self._export_progress)
        worker.completed.connect(self._export_completed)
        worker.failed.connect(self._export_failed)
        worker.start()

    def _export_progress(self, current, total, name):
        self.progress.setValue(current)
        self.job_status.setText(f"Creating export {current}/{total}: {name}")

    def _export_completed(self, result):
        self._busy = False
        self._set_job_busy(False)
        self.progress.hide()
        details = f"Exported {len(result.processed)} photo(s)."
        if result.failed:
            details += "\n\nSome files could not be exported:\n" + "\n".join(
                f"{path.name}: {error}" for path, error in result.failed[:10]
            )
        self.job_status.setText(details.replace("\n", " "))
        if result.failed:
            QMessageBox.warning(self, "Export finished with issues", details)
        else:
            QMessageBox.information(self, "Export complete", details)

    def _export_failed(self, message):
        self._busy = False
        self._set_job_busy(False)
        self.progress.hide()
        self.job_status.setText("Photo export did not finish.")
        QMessageBox.critical(self, "Could not export selected photos", message)

    def closeEvent(self, event):
        active_workers = [
            worker for worker in (self._worker, *self._preview_workers)
            if worker is not None and worker.isRunning()
        ]
        if active_workers:
            QMessageBox.information(
                self, "Work in progress",
                "Wait for the catalog scan, preview, or export to finish before closing this window.",
            )
            event.ignore()
            return
        super().closeEvent(event)
