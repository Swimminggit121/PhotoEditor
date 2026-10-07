from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QApplication,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.batch_processor import BatchProcessor
from core.style_match import build_style_profile
from image.loader import is_supported
from presets.manager import load_preset


class BatchWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)

    def __init__(self, processor: BatchProcessor):
        super().__init__()
        self.processor = processor

    @Slot()
    def run(self):
        def callback(current, total, path):
            self.progress.emit(current, total, path.name)

        self.finished.emit(self.processor.run(callback))


class BatchEditorDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.processor = None
        self.thread = None
        self.worker = None
        self.setWindowTitle("Professional Batch Edit")
        self.setMinimumSize(620, 420)
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        self.resize(760, min(680, available.height() - 80) if available else 680)

        self.input_edit = QLineEdit()
        self.input_edit.setReadOnly(True)
        self.input_edit.setPlaceholderText("Choose a folder containing your photos")
        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("Choose where edited copies should be saved")
        self.photo_count = QLabel("Choose a photo folder to begin.")
        self.mode = QComboBox()
        self.mode.addItem("Professional Auto Edit", "professional")
        self.mode.addItem("Full Auto Edit", "auto_edit")
        self.mode.addItem("Auto Colour Grade", "auto_grade")
        self.mode.addItem("Current Preset", "preset")
        self.mode.addItem("Reference Style", "reference")

        self.quality = QComboBox()
        self.quality.addItems(["100", "95", "90", "85"])
        self.quality.setCurrentText("95")
        self.recursive = QCheckBox("Include subfolders")
        self.preset_edit = QLineEdit()
        self.preset_edit.setPlaceholderText("Select a saved preset JSON file")
        self.preset_button = None
        self.reference_label = QLabel("Uses the currently active photo as the reference style for the whole batch.")
        self.reference_label.setWordWrap(True)
        self.progress = QProgressBar()
        self.status = QLabel("Choose an input folder and output folder to prepare a professional upload set.")
        self.status.setWordWrap(True)
        self.start_button = QPushButton("Start Batch")
        self.start_button.setDefault(True)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)

        folders = QGroupBox("Folders")
        folders_layout = QFormLayout(folders)
        folders_layout.addRow("Photo folder", self._browse_row(self.input_edit, True))
        folders_layout.addRow("", self.photo_count)
        folders_layout.addRow("Output folder", self._browse_row(self.output_edit, False))

        style_box = QGroupBox("Edit profile")
        style_layout = QFormLayout(style_box)
        style_layout.addRow("Processing mode", self.mode)
        style_layout.addRow("Export quality", self.quality)
        style_layout.addRow("", self.recursive)
        style_layout.addRow("Preset JSON", self._preset_row())
        style_layout.addRow("Reference", self.reference_label)

        buttons = QDialogButtonBox()
        buttons.addButton(self.start_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(self.cancel_button, QDialogButtonBox.RejectRole)
        buttons.rejected.connect(self.cancel)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(folders)
        content_layout.addWidget(style_box)
        content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll, 1)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        layout.addWidget(buttons)

        self.mode.currentIndexChanged.connect(self._update_mode_ui)
        self.recursive.toggled.connect(self._update_photo_count)
        self.start_button.clicked.connect(self.start)
        self._update_mode_ui()

    def _browse_row(self, edit, input_folder):
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("Choose Photos Folder..." if input_folder else "Choose Output Folder...")
        button.clicked.connect(lambda: self._browse_folder(edit, input_folder))
        row.addWidget(edit)
        row.addWidget(button)
        return container

    def _browse_folder(self, edit, input_folder):
        title = "Choose Photo Folder" if input_folder else "Choose Output Folder"
        path = QFileDialog.getExistingDirectory(self, title)
        if path:
            edit.setText(path)
            if input_folder and not self.output_edit.text():
                edit_path = Path(path)
                self.output_edit.setText(str(edit_path.parent / (edit_path.name + "_edited")))
            self._update_photo_count()

    def _preset_row(self):
        container = QWidget()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.preset_button = QPushButton("Choose Preset...")
        self.preset_button.clicked.connect(self.choose_preset)
        row.addWidget(self.preset_edit)
        row.addWidget(self.preset_button)
        container.setLayout(row)
        return container

    def choose_preset(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Preset", "", "PhotoEditor Preset (*.json)"
        )
        if path:
            self.preset_edit.setText(path)

    def _update_mode_ui(self):
        enabled = self.mode.currentData() == "preset"
        self.preset_edit.setEnabled(enabled)
        self.preset_button.setEnabled(enabled)

    def _update_photo_count(self):
        input_dir = Path(self.input_edit.text()) if self.input_edit.text() else None
        if input_dir is None or not input_dir.is_dir():
            self.photo_count.setText("Choose a photo folder to begin.")
            return
        iterator = input_dir.rglob("*") if self.recursive.isChecked() else input_dir.iterdir()
        supported = sum(1 for path in iterator if path.is_file() and is_supported(path))
        self.photo_count.setText(f"{supported} supported photo{'s' if supported != 1 else ''} found.")

    def start(self):
        input_dir = Path(self.input_edit.text().strip())
        output_text = self.output_edit.text().strip()
        output_dir = Path(output_text) if output_text else None
        if not input_dir.is_dir():
            QMessageBox.warning(self, "Professional Batch Edit", "Choose a valid photo folder.")
            return
        if output_dir is None:
            QMessageBox.warning(self, "Professional Batch Edit", "Choose an output folder.")
            return
        if input_dir.resolve() == output_dir.resolve():
            QMessageBox.warning(self, "Professional Batch Edit", "Choose a separate output folder so your source photos stay untouched.")
            return

        mode = self.mode.currentData()
        preset = None
        reference = None

        try:
            if mode == "preset":
                if not self.preset_edit.text():
                    raise ValueError("Choose a preset JSON file.")
                preset = load_preset(self.preset_edit.text())
            elif mode == "reference":
                if not self.window.document.has_image():
                    raise ValueError("Open and edit a reference photo before using Reference Style.")
                reference = build_style_profile(self.window.document.adjustments)

            self.processor = BatchProcessor(
                input_dir,
                output_dir,
                mode=mode,
                quality=int(self.quality.currentText()),
                recursive=self.recursive.isChecked(),
                preset=preset,
                reference=reference,
            )
            total = len(self.processor.files())
            if total == 0:
                QMessageBox.information(self, "Professional Batch Edit", "No supported photos were found in the selected folder.")
                return

            self.progress.setRange(0, total)
            self.progress.setValue(0)
            self.status.setText(f"Ready to process {total} photos.")
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)

            self.thread = QThread(self)
            self.worker = BatchWorker(self.processor)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.progress.connect(self.update_progress)
            self.worker.finished.connect(self.finished)
            self.worker.finished.connect(self.thread.quit)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.finished.connect(self.worker.deleteLater)
            self.thread.start()
        except Exception as exc:
            QMessageBox.critical(self, "Batch Auto Edit", str(exc))

    @Slot(int, int, str)
    def update_progress(self, current, total, name):
        self.progress.setValue(current)
        self.status.setText(f"Processing {current} / {total}: {name}")

    @Slot(object)
    def finished(self, result):
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if result.cancelled:
            self.status.setText(f"Cancelled after {len(result.processed)} photos.")
        elif result.failed:
            self.status.setText(
                f"Finished: {len(result.processed)} exported, {len(result.failed)} failed."
            )
            details = "\n".join(f"{path.name}: {error}" for path, error in result.failed[:12])
            QMessageBox.warning(
                self,
                "Batch completed with errors",
                f"Exported {len(result.processed)} photos.\n"
                f"Failed: {len(result.failed)}\n\n{details}",
            )
        else:
            self.status.setText(f"Finished: {len(result.processed)} photos exported.")
            QMessageBox.information(
                self,
                "Batch Auto Edit",
                f"Successfully exported {len(result.processed)} photos.",
            )

    def cancel(self):
        if self.processor:
            self.processor.cancel()
            self.status.setText("Cancelling after the current photo...")
        else:
            self.reject()

    def closeEvent(self, event):
        if self.processor and self.thread and self.thread.isRunning():
            self.processor.cancel()
            event.ignore()
        else:
            event.accept()
