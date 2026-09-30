from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QCheckBox,
    QVBoxLayout,
)

from core.batch_processor import BatchProcessor
from core.style_match import build_style_profile
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
        self.setWindowTitle("Batch Auto Edit")
        self.setMinimumWidth(620)

        self.input_edit = QLineEdit()
        self.output_edit = QLineEdit()
        self.mode = QComboBox()
        self.mode.addItem("Full Auto Edit", "auto_edit")
        self.mode.addItem("Auto Colour Grade", "auto_grade")
        self.mode.addItem("Current Preset", "preset")
        self.mode.addItem("Reference Style", "reference")

        self.quality = QComboBox()
        self.quality.addItems(["100", "95", "90", "85"])
        self.quality.setCurrentText("95")
        self.recursive = QCheckBox("Include subfolders")
        self.preset_edit = QLineEdit()
        self.reference_label = QLabel("Uses the currently edited photo as the reference style.")
        self.progress = QProgressBar()
        self.status = QLabel("Choose an input and output folder.")
        self.start_button = QPushButton("Start")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)

        form = QFormLayout()
        form.addRow("Input folder", self._browse_row(self.input_edit, True))
        form.addRow("Output folder", self._browse_row(self.output_edit, False))
        form.addRow("Editing mode", self.mode)
        form.addRow("JPEG quality", self.quality)
        form.addRow("", self.recursive)
        form.addRow("Preset JSON", self._preset_row())
        form.addRow("Reference", self.reference_label)

        buttons = QDialogButtonBox()
        buttons.addButton(self.start_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(self.cancel_button, QDialogButtonBox.RejectRole)
        buttons.rejected.connect(self.cancel)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        layout.addWidget(buttons)

        self.mode.currentIndexChanged.connect(self._update_mode_ui)
        self.start_button.clicked.connect(self.start)
        self._update_mode_ui()

    def _browse_row(self, edit, input_folder):
        row = QHBoxLayout()
        button = QPushButton("Browse...")
        button.clicked.connect(lambda: self._browse_folder(edit, input_folder))
        row.addWidget(edit)
        row.addWidget(button)
        wrapper = QHBoxLayout()
        wrapper.addLayout(row)
        container = QLabel()
        container.setLayout(wrapper)
        return container

    def _browse_folder(self, edit, input_folder):
        path = QFileDialog.getExistingDirectory(self, "Choose Folder")
        if path:
            edit.setText(path)
            if input_folder and not self.output_edit.text():
                edit_path = Path(path)
                self.output_edit.setText(str(edit_path.parent / (edit_path.name + "_edited")))

    def _preset_row(self):
        row = QHBoxLayout()
        button = QPushButton("Choose...")
        button.clicked.connect(self.choose_preset)
        row.addWidget(self.preset_edit)
        row.addWidget(button)
        container = QLabel()
        container.setLayout(row)
        return container

    def choose_preset(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Preset", "", "PhotoEditor Preset (*.json)"
        )
        if path:
            self.preset_edit.setText(path)

    def _update_mode_ui(self):
        self.preset_edit.setEnabled(self.mode.currentData() == "preset")

    def start(self):
        input_dir = Path(self.input_edit.text().strip())
        output_dir = Path(self.output_edit.text().strip())
        if not input_dir.is_dir():
            QMessageBox.warning(self, "Batch Auto Edit", "Choose a valid input folder.")
            return
        if not output_dir:
            QMessageBox.warning(self, "Batch Auto Edit", "Choose an output folder.")
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
                QMessageBox.information(self, "Batch Auto Edit", "No supported photos were found.")
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
