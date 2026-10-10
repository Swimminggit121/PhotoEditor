from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QVBoxLayout,
)

from ai.analysis import analyze_image
from ai.enhance import enhance
from ai.masks import mask_to_local_adjustment, sky_mask, subject_mask
from ai.runtime import runtime_info
from ai.smart_crop import smart_crop
from ai.style import reference_grade, reference_similarity
from core.auto_grade import auto_edit


class TaskWorker(QObject):
    completed = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, key, function):
        super().__init__()
        self.key = key
        self.function = function

    @Slot()
    def run(self):
        try:
            self.completed.emit(self.key, self.function())
        except Exception as exc:
            self.failed.emit(self.key, str(exc))


class AIPanel(QGroupBox):
    analysis_ready = Signal(object)
    mask_ready = Signal(object)
    grade_ready = Signal(object)
    crop_ready = Signal(object)
    enhancement_ready = Signal(object)

    def __init__(self, window, parent=None):
        super().__init__("AI Studio", parent)
        self.window = window
        self.thread = None
        self.worker = None
        self._busy = False
        self._buttons = []

        layout = QVBoxLayout(self)
        self.status = QLabel("AI ready")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.backend = QLabel("")
        self.backend.setWordWrap(True)
        layout.addWidget(self.backend)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        self._add_button(layout, "Analyse Current Photo", self.analyse)
        row = QHBoxLayout()
        self._add_button(row, "Subject Mask", self.subject)
        self._add_button(row, "Sky Mask", self.sky)
        self._add_button(row, "Smart Crop", self.crop)
        layout.addLayout(row)

        row2 = QHBoxLayout()
        self.ratio = QComboBox()
        self.ratio.addItems(["1:1", "4:5", "4:3", "3:2", "16:9", "9:16"])
        row2.addWidget(self.ratio)
        self._add_button(row2, "Crop", self.crop)
        layout.addLayout(row2)

        self._add_button(layout, "Auto AI Grade", self.auto_grade)
        self._add_button(layout, "Match Reference...", self.reference)
        row3 = QHBoxLayout()
        self._add_button(row3, "Denoise", lambda: self.enhance(0.35, 1))
        self._add_button(row3, "2× Upscale", lambda: self.enhance(0, 2))
        layout.addLayout(row3)

        info = runtime_info()
        self.backend.setText(
            f"Runtime: {'CUDA / ' + info.gpu_name if info.cuda else 'CPU'} | "
            f"Detector: {'installed' if info.ultralytics else 'optional'}"
        )

    def _add_button(self, parent_layout, label, callback):
        button = QPushButton(label)
        button.clicked.connect(callback)
        parent_layout.addWidget(button)
        self._buttons.append(button)
        return button

    def image(self):
        document = self.window.document
        if not document.has_image():
            return None
        image = getattr(document, "working_image", None) or document.original_image
        return image

    def _run_task(self, key, function, message):
        if self._busy:
            self.status.setText("Another AI operation is already running.")
            return
        image = self.image()
        if image is None:
            QMessageBox.information(self, "AI Studio", "Open an image first.")
            return
        self._busy = True
        self.progress.show()
        self.status.setText(message)
        for button in self._buttons:
            button.setEnabled(False)
        self.thread = QThread(self)
        self.worker = TaskWorker(key, function)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.completed.connect(self._task_done)
        self.worker.failed.connect(self._task_failed)
        self.worker.completed.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._thread_finished)
        self.thread.start()

    @Slot(str, object)
    def _task_done(self, key, result):
        self._busy = False
        self.progress.hide()
        for button in self._buttons:
            button.setEnabled(True)
        if key == "analyse":
            self.status.setText(
                f"{result.scene} | Quality {result.quality_score:.0f}/100 | "
                f"Faces {result.faces} | Sky {result.sky_fraction * 100:.0f}% | {result.backend}"
            )
            self.analysis_ready.emit(result)
        elif key in ("subject", "sky"):
            self.mask_ready.emit(result)
            self.status.setText("AI mask created. Apply local adjustments in the Masks panel.")
        elif key == "crop":
            self.crop_ready.emit(result)
            self.status.setText(f"Smart crop ready ({result.score:.0f}/100).")
        elif key in ("grade", "reference"):
            if key == "reference":
                similarity, adjustments = result
                self.status.setText(f"Reference similarity: {similarity * 100:.1f}%")
                self.grade_ready.emit(adjustments)
            else:
                self.grade_ready.emit(result)
                self.status.setText("AI-assisted grade applied; values remain editable.")
        elif key == "enhance":
            self.enhancement_ready.emit(result)
            self.status.setText("Enhancement completed; original photo is preserved.")
        self.worker = None

    @Slot(str, str)
    def _task_failed(self, key, message):
        self._busy = False
        self.progress.hide()
        for button in self._buttons:
            button.setEnabled(True)
        self.status.setText("AI operation failed. You can try again.")
        QMessageBox.warning(self, "AI Studio", f"{key.title()} failed:\n{message}")
        self.worker = None

    @Slot()
    def _thread_finished(self):
        thread = self.thread
        self.thread = None
        if thread is not None:
            thread.deleteLater()

    def analyse(self):
        image = self.image()
        if image is not None:
            snapshot = image.copy()
            self._run_task("analyse", lambda: analyze_image(snapshot, True), "Analysing photo...")

    def subject(self):
        image = self.image()
        if image is not None:
            snapshot = image.copy()
            self._run_task("subject", lambda: mask_to_local_adjustment(subject_mask(snapshot), "AI Subject"), "Creating subject mask...")

    def sky(self):
        image = self.image()
        if image is not None:
            snapshot = image.copy()
            self._run_task("sky", lambda: mask_to_local_adjustment(sky_mask(snapshot), "AI Sky"), "Creating sky mask...")

    def crop(self):
        image = self.image()
        if image is not None:
            snapshot = image.copy()
            width, height = map(float, self.ratio.currentText().split(":"))
            self._run_task("crop", lambda: smart_crop(snapshot, width / height, True), "Finding a subject-aware crop...")

    def auto_grade(self):
        image = self.image()
        if image is not None:
            snapshot = image.copy()
            self._run_task("grade", lambda: auto_edit(snapshot), "Building an automatic grade...")

    def reference(self):
        image = self.image()
        if image is None:
            QMessageBox.information(self, "AI Studio", "Open an image first.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Reference Image", "",
            "Images (*.jpg *.jpeg *.png *.tif *.tiff *.webp)",
        )
        if not path:
            return
        try:
            from PIL import Image
            with Image.open(path) as reference:
                reference_image = reference.convert("RGB").copy()
            source = image.copy()
            self._run_task(
                "reference",
                lambda: (reference_similarity(source, reference_image), reference_grade(source, reference_image)),
                "Matching reference style...",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Reference Match", str(exc))

    def enhance(self, denoise_strength, scale):
        image = self.image()
        if image is not None:
            snapshot = image.copy()
            self._run_task(
                "enhance",
                lambda: enhance(snapshot, float(denoise_strength), int(scale)),
                "Enhancing photo...",
            )
