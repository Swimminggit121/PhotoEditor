from __future__ import annotations

from pathlib import Path

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from image.loader import is_supported
from processing.montage import TEMPLATES, generate_reel_video
from processing.photo_duplicates import (
    PhotoDuplicateGroup,
    collect_photo_paths,
    find_duplicate_groups,
    load_oriented_photo,
)
from ui.audio_library_dialog import AudioLibraryDialog


class _ScanWorker(QThread):
    progress = Signal(int, int, str)

    def __init__(self, inputs, recursive, parent=None):
        super().__init__(parent)
        self.inputs = inputs
        self.recursive = recursive
        self.photos = []
        self.duplicates = []
        self.error: str | None = None

    def run(self):
        try:
            photos = collect_photo_paths(self.inputs, recursive=self.recursive)
            if not photos:
                raise ValueError("No supported photos were found in the selected files or folders.")

            def update(current, total, name):
                self.progress.emit(current, total, name.name)

            duplicates = find_duplicate_groups(photos, progress=update)
            self.photos = photos
            self.duplicates = duplicates
        except Exception as exc:
            self.error = str(exc)


class _RenderWorker(QThread):
    progress = Signal(int, int, str)

    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.options = options
        self.output: str | None = None
        self.error: str | None = None

    def run(self):
        try:
            self.options["progress"] = self.progress.emit
            result = generate_reel_video(**self.options)
            self.output = str(result)
        except Exception as exc:
            self.error = str(exc)


class DuplicateReviewDialog(QDialog):
    def __init__(self, groups: list[PhotoDuplicateGroup], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Review visually similar photos")
        self.setMinimumSize(780, min(720, 240 + len(groups) * 124))
        self.groups = groups
        self.decisions: list[QComboBox] = []

        heading = QLabel(
            f"Found {len(groups)} groups of visually similar photos. Choose what to include in the video "
            "for every group. Source files are never changed or deleted."
        )
        heading.setWordWrap(True)
        self.table = QTableWidget(len(groups), 3)
        self.table.setHorizontalHeaderLabels(["Similar photos", "Visual match", "Video choice"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 485)
        self.table.setColumnWidth(1, 105)
        self.table.verticalHeader().setDefaultSectionSize(104)

        for row, group in enumerate(groups):
            previews = QWidget()
            preview_layout = QHBoxLayout(previews)
            preview_layout.setContentsMargins(6, 4, 6, 4)
            for path in group.paths:
                entry = QWidget()
                entry_layout = QHBoxLayout(entry)
                entry_layout.setContentsMargins(0, 0, 0, 0)
                thumbnail = QLabel()
                thumbnail.setFixedSize(70, 70)
                thumbnail.setAlignment(Qt.AlignCenter)
                try:
                    image = load_oriented_photo(path)
                    image.thumbnail((68, 68), Image.Resampling.LANCZOS)
                    thumbnail.setPixmap(QPixmap.fromImage(ImageQt(image)))
                except Exception:
                    thumbnail.setText("Preview unavailable")
                name = QLabel(path.name)
                name.setToolTip(str(path))
                name.setWordWrap(True)
                entry_layout.addWidget(thumbnail)
                entry_layout.addWidget(name)
                preview_layout.addWidget(entry, 1)
            preview_layout.addStretch(1)
            self.table.setCellWidget(row, 0, previews)
            self.table.setItem(row, 1, QTableWidgetItem(f"~{group.similarity:.1f}%"))
            choice = QComboBox()
            choice.addItem("Choose for this group…", None)
            choice.addItem("Include every copy", "all")
            choice.addItem("Keep first photo only", "first")
            choice.currentIndexChanged.connect(self._update_accept_state)
            self.table.setCellWidget(row, 2, choice)
            self.decisions.append(choice)

        controls = QHBoxLayout()
        include_all = QPushButton("Include all copies")
        keep_one = QPushButton("Keep one per group")
        include_all.clicked.connect(lambda: self._set_all("all"))
        keep_one.clicked.connect(lambda: self._set_all("first"))
        controls.addWidget(include_all)
        controls.addWidget(keep_one)
        controls.addStretch(1)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addWidget(heading)
        layout.addLayout(controls)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.buttons)

    def _set_all(self, decision):
        for choice in self.decisions:
            choice.setCurrentIndex(choice.findData(decision))

    def _update_accept_state(self):
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(
            all(choice.currentData() is not None for choice in self.decisions)
        )

    def chosen_paths(self) -> list[Path]:
        included = []
        for group, choice in zip(self.groups, self.decisions):
            included.extend(group.paths if choice.currentData() == "all" else group.paths[:1])
        return included


class VideoMontageDialog(QDialog):
    def __init__(self, window, suite_mode: bool = False, initial_paths=None):
        super().__init__(window)
        self.window = window
        self.suite_mode = suite_mode
        self.setWindowTitle("Create a Photo Video")
        self.setMinimumSize(760, 700)
        self._scan_worker: _ScanWorker | None = None
        self._render_worker: _RenderWorker | None = None
        self._photo_paths: list[Path] = []
        self._options = {}

        self.input_summary = QLabel("Add individual photos or a folder. Folder scans include subfolders.")
        self.input_summary.setWordWrap(True)
        self.photo_list = QListWidget()
        self.photo_list.setMaximumHeight(118)
        add_photos = QPushButton("Add photos…")
        add_folder = QPushButton("Add folder…")
        remove_photos = QPushButton("Remove selected")
        clear_photos = QPushButton("Clear")
        add_photos.clicked.connect(self._add_photos)
        add_folder.clicked.connect(self._add_folder)
        remove_photos.clicked.connect(self._remove_selected)
        clear_photos.clicked.connect(self._clear_inputs)
        source_actions = QHBoxLayout()
        for button in (add_photos, add_folder, remove_photos, clear_photos):
            source_actions.addWidget(button)
        source_actions.addStretch(1)
        self.recursive = QCheckBox("Include subfolders")
        self.recursive.setChecked(True)

        self.output_edit = QLineEdit()
        output_button = QPushButton("Choose…")
        output_button.clicked.connect(self._browse_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(output_button)

        self.audio_edit = QLineEdit()
        self.audio_edit.setPlaceholderText("Required: your own soundtrack or a licensed track")
        audio_button = QPushButton("Choose audio…")
        audio_button.clicked.connect(self._browse_audio)
        library_button = QPushButton("Browse CC0 library…")
        library_button.clicked.connect(self._open_audio_library)
        audio_row = QHBoxLayout()
        audio_row.addWidget(self.audio_edit, 1)
        audio_row.addWidget(audio_button)
        audio_row.addWidget(library_button)

        files = QGroupBox("Photo sequence")
        self.file_group = files
        files_layout = QVBoxLayout(files)
        files_layout.addWidget(self.input_summary)
        files_layout.addLayout(source_actions)
        files_layout.addWidget(self.photo_list)
        files_layout.addWidget(self.recursive)
        files_layout.addLayout(self._form_row("Output video", output_row))
        files_layout.addLayout(self._form_row("Soundtrack", audio_row))

        self.template = QComboBox()
        self.template.addItems(TEMPLATES)
        self.template.currentIndexChanged.connect(self._apply_template)
        self.template_hint = QLabel()
        self.template_hint.setWordWrap(True)
        self.aspect_ratio = QComboBox()
        self.aspect_ratio.addItems(["9:16", "1:1", "4:5", "16:9", "4:3"])
        self.aspect_ratio.setCurrentText("9:16")
        self.duration = QLineEdit()
        self.transition = QLineEdit()
        self.fps = QLineEdit("30")
        self.audio_volume = QLineEdit("0.35")
        self.use_current_edit = QCheckBox("Apply this Photo Editor's current adjustments to every photo")
        self.use_current_edit.setEnabled(
            hasattr(self.window, "document") and self.window.document.has_image()
        )
        self.auto_edit = QCheckBox("Auto-edit each photo before building the video (Suite only)")
        self.auto_edit.setVisible(suite_mode)
        settings = QGroupBox("Video style and export")
        self.settings_group = settings
        settings_layout = QFormLayout(settings)
        settings_layout.addRow("Template", self.template)
        settings_layout.addRow("Style notes", self.template_hint)
        settings_layout.addRow("Aspect ratio", self.aspect_ratio)
        settings_layout.addRow("Seconds per photo", self.duration)
        settings_layout.addRow("Transition seconds", self.transition)
        settings_layout.addRow("Frames per second", self.fps)
        settings_layout.addRow("Soundtrack volume (0–2)", self.audio_volume)
        settings_layout.addRow("", self.use_current_edit)
        if suite_mode:
            settings_layout.addRow("", self.auto_edit)

        self.status = QLabel("Choose photos, review any visual duplicates, then create your video.")
        self.status.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Review photos and create")
        buttons.accepted.connect(self.start)
        buttons.rejected.connect(self._cancel_or_close)
        self.buttons = buttons

        layout = QVBoxLayout(self)
        layout.addWidget(files)
        layout.addWidget(settings)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        note = QLabel(
            "Templates add animated photo moves and intentional transitions. Photo mode uses your prepared "
            "images; only the full Suite offers optional per-photo auto editing. Your selected source files "
            "are not changed. Music must be your own or licensed."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addWidget(buttons)
        self._apply_template(self.template.currentIndex())
        if initial_paths:
            self._add_inputs(initial_paths)
            self._set_default_output()

    @staticmethod
    def _form_row(label, row_layout):
        wrapper = QHBoxLayout()
        wrapper.addWidget(QLabel(label))
        wrapper.addLayout(row_layout, 1)
        return wrapper

    def _add_photos(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose photos",
            "",
            "Image files (*.jpg *.jpeg *.png *.tif *.tiff *.webp *.bmp *.gif *.heic *.heif *.avif "
            "*.dng *.cr2 *.cr3 *.nef *.nrw *.arw *.srf *.sr2 *.raf *.orf *.rw2 *.pef *.3fr *.fff "
            "*.iiq *.kdc *.dcr *.mos *.mrw *.mef *.x3f *.erf *.rwl *.srw *.bay *.cap *.eip *.gpr "
            "*.r3d *.ari *.braw *.cin *.dpx *.exr *.hdr *.j2k *.jp2 *.jpf *.jpx *.j2c *.jng "
            "*.mng *.pbm *.pfm *.pgm *.pnm *.ppm *.psd *.pxr *.ras *.sgi *.tga *.vda *.icb *.vst "
            "*.webp *.wmf *.emf);;All files (*.*)",
        )
        if paths:
            self._add_inputs(paths)
            self._set_default_output()

    def _add_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Choose photo folder")
        if path:
            self._add_inputs([path])
            self._set_default_output()

    def _add_inputs(self, paths):
        existing = {
            self.photo_list.item(index).text().casefold()
            for index in range(self.photo_list.count())
        }
        for path in paths:
            resolved = str(Path(path).expanduser().resolve())
            if resolved.casefold() in existing:
                continue
            if Path(resolved).is_file() and not is_supported(Path(resolved)):
                continue
            self.photo_list.addItem(resolved)
            existing.add(resolved.casefold())
        count = self.photo_list.count()
        self.input_summary.setText(
            f"{count} photo file/folder source(s) selected. Folder contents are decoded and visually checked "
            "before export; duplicate groups require a choice."
        )

    def _remove_selected(self):
        for item in self.photo_list.selectedItems():
            self.photo_list.takeItem(self.photo_list.row(item))
        self._update_input_summary()

    def _clear_inputs(self):
        self.photo_list.clear()
        self._update_input_summary()

    def _update_input_summary(self):
        count = self.photo_list.count()
        self.input_summary.setText(
            "Add individual photos or a folder. Folder scans include subfolders."
            if count == 0 else f"{count} photo file/folder source(s) selected."
        )

    def _set_default_output(self):
        if not self.output_edit.text().strip():
            first = Path(self.photo_list.item(0).text())
            originals = first if first.is_dir() else first.parent
            export_folder = originals.parent / f"{originals.name}_Edited"
            self.output_edit.setText(str(export_folder / "photo-video.mp4"))

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save video", "photo-video.mp4", "Video (*.mp4 *.mov)"
        )
        if path:
            self.output_edit.setText(path)

    def _browse_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose soundtrack", "",
            "Audio (*.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus)",
        )
        if path:
            self.audio_edit.setText(path)

    def _open_audio_library(self):
        dialog = AudioLibraryDialog(self)
        dialog.audio_added.connect(self.audio_edit.setText)
        dialog.exec()

    def _apply_template(self, index):
        name = self.template.itemText(index)
        if name in TEMPLATES:
            duration, transition, _ = TEMPLATES[name]
            self.duration.setText(str(duration))
            self.transition.setText(str(transition))
        self.template_hint.setText({
            "Cinematic push": "A slow, gentle zoom with dissolves for polished travel and portrait sequences.",
            "Story drift": "A soft drifting pull-back with short dissolves for a relaxed narrative pace.",
            "Dynamic snap": "Quick alternating push-ins and direct cuts for energetic highlight recaps.",
            "Memory flash": "Subtle motion with brief white-flash transitions for event and memory montages.",
        }.get(name, "Select a motion and transition style for the photo sequence."))

    def start(self):
        if self._scan_worker and self._scan_worker.isRunning():
            return
        try:
            inputs = [self.photo_list.item(index).text() for index in range(self.photo_list.count())]
            if not inputs:
                raise ValueError("Add at least one photo or photo folder.")
            output = Path(self.output_edit.text().strip()).expanduser()
            if not output.name:
                raise ValueError("Choose an output video path.")
            audio_path = self.audio_edit.text().strip()
            if not audio_path or not Path(audio_path).expanduser().is_file():
                raise ValueError("Choose your own soundtrack or download a licensed track from the CC0 library.")
            audio_volume = float(self.audio_volume.text())
            fps = int(float(self.fps.text()))
            duration = float(self.duration.text())
            transition = float(self.transition.text())
            if not 0 <= audio_volume <= 2:
                raise ValueError("Soundtrack volume must be from 0 to 2.")
            if fps <= 0:
                raise ValueError("Frames per second must be a positive number.")
            if duration <= 0 or transition < 0:
                raise ValueError("Photo duration must be positive and transition time cannot be negative.")
            template = self.template.currentText()
            current_adjustments = (
                self.window.document.adjustments.copy()
                if self.use_current_edit.isChecked()
                and hasattr(self.window, "document")
                and self.window.document.has_image()
                else None
            )
            if self.auto_edit.isChecked() and current_adjustments is not None:
                raise ValueError(
                    "Choose either the current photo adjustments or automatic per-photo editing, not both."
                )
            self._options = {
                "input_dir": None,
                "photo_paths": None,
                "recursive": self.recursive.isChecked(),
                "output_file": output,
                "aspect_ratio": self.aspect_ratio.currentText(),
                "fps": fps,
                "duration_per_photo": duration,
                "transition_duration": transition,
                "audio_path": audio_path,
                "audio_volume": audio_volume,
                "template": template,
                "auto_grade_photos": self.auto_edit.isChecked(),
                "adjustments": current_adjustments,
            }
            self._set_busy(True)
            self.progress.setValue(0)
            self.progress.show()
            self.status.setText("Analyzing image content for visually similar photos…")
            self._scan_worker = _ScanWorker(inputs, self.recursive.isChecked(), self)
            self._scan_worker.progress.connect(self._scan_progress)
            self._scan_worker.finished.connect(self._scan_finished)
            self._scan_worker.start()
        except Exception as exc:
            QMessageBox.warning(self, "Check photo video settings", str(exc))

    def _scan_progress(self, current, total, name):
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self.status.setText(f"Checking photo content {current}/{total}: {name}")

    def _scan_finished(self):
        worker = self._scan_worker
        if worker is None:
            return
        if worker.error:
            self._job_failed(worker.error)
        else:
            self._scan_complete(worker.photos, worker.duplicates)

    def _scan_complete(self, paths, duplicate_groups):
        self._photo_paths = paths
        if duplicate_groups:
            review = DuplicateReviewDialog(duplicate_groups, self)
            if review.exec() != QDialog.Accepted:
                self._set_busy(False)
                self.status.setText("Video creation cancelled during duplicate review.")
                return
            duplicates = {path for group in duplicate_groups for path in group.paths}
            retained = set(review.chosen_paths())
            self._photo_paths = [
                path for path in paths if path not in duplicates or path in retained
            ]
        if not self._photo_paths:
            self._job_failed("No photos remain after duplicate review.")
            return
        self._options["photo_paths"] = self._photo_paths
        self._options["input_dir"] = None
        self.status.setText(f"Building a video from {len(self._photo_paths)} selected photos…")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self._render_worker = _RenderWorker(self._options, self)
        self._render_worker.progress.connect(self._render_progress)
        self._render_worker.finished.connect(self._render_finished)
        self._render_worker.start()

    def _render_finished(self):
        worker = self._render_worker
        if worker is None:
            return
        if worker.error:
            self._job_failed(worker.error)
        elif worker.output:
            self._render_complete(worker.output)
        else:
            self._job_failed("The video export ended without an output path.")

    def _render_progress(self, current, total, name):
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self.status.setText(f"Rendering {current}/{total} frames · {name}")

    def _render_complete(self, result):
        rendered = Path(result)
        if hasattr(self.window, "status_label"):
            self.window.status_label.setText(f"Photo video exported: {rendered.name}")
        QMessageBox.information(self, "Video created", f"Video saved to:\n{rendered}")
        self.accept()

    def _job_failed(self, message):
        self._set_busy(False)
        self.status.setText("Could not complete the photo video.")
        QMessageBox.critical(self, "Photo video failed", message)

    def _set_busy(self, busy):
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(not busy)
        self.buttons.button(QDialogButtonBox.Cancel).setEnabled(not busy)
        self.file_group.setEnabled(not busy)
        self.settings_group.setEnabled(not busy)
        if not busy:
            self.progress.hide()

    def _cancel_or_close(self):
        worker_running = (
            self._scan_worker is not None and self._scan_worker.isRunning()
        ) or (
            self._render_worker is not None and self._render_worker.isRunning()
        )
        if not worker_running:
            self.reject()

    def closeEvent(self, event):
        worker_running = (
            self._scan_worker is not None and self._scan_worker.isRunning()
        ) or (
            self._render_worker is not None and self._render_worker.isRunning()
        )
        if worker_running:
            self.status.setText("Please wait for the current photo analysis or video export to finish.")
            event.ignore()
            return
        super().closeEvent(event)
