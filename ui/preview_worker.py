from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from PySide6.QtWidgets import QApplication

from core.document import make_preview_source
from core.renderer import render_image
import numpy as np
from PIL import Image


def _display_image(image):
    if isinstance(image, Image.Image):
        return image
    pixels = np.asarray(image)
    if np.issubdtype(pixels.dtype, np.integer):
        pixels = np.rint(pixels.astype(np.float32) / np.iinfo(pixels.dtype).max * 255)
    else:
        pixels = np.rint(np.clip(pixels, 0, 1) * 255)
    return Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8), "RGB")


class PreviewSignals(QObject):
    ready = Signal(int, object, object, object, bool)
    failed = Signal(int, str)


class PreviewTask(QRunnable):
    def __init__(self, generation, original_image, adjustments, max_size, cached_source=None, precision_source=None):
        super().__init__()
        self.generation = generation
        self.original_image = original_image
        self.source_image = (
            precision_source
            if precision_source is not None
            else (cached_source or original_image)
        )
        self.adjustments = adjustments
        self.max_size = max_size
        self.signals = PreviewSignals(QApplication.instance())

    @Slot()
    def run(self):
        try:
            preview_source = (
                self.source_image if self.max_size is None
                else make_preview_source(self.source_image, self.max_size)
            )
            rendered = render_image(preview_source, self.adjustments)
            self.signals.ready.emit(
                self.generation,
                self.original_image,
                _display_image(preview_source),
                _display_image(rendered),
                self.max_size is None,
            )
        except Exception as exc:
            self.signals.failed.emit(self.generation, str(exc))
