from pathlib import Path
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QWidget


class HistogramWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.histograms = None
        self.setMinimumHeight(150)

    def set_image(self, image):
        if image is self.image:
            return
        self.image = image
        if image is None:
            self.histograms = None
        else:
            array = np.asarray(image.convert("RGB"), dtype=np.uint8)
            self.histograms = [
                np.histogram(channel, bins=256, range=(0, 255))[0]
                for channel in (array[..., 0], array[..., 1], array[..., 2])
            ]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        if self.image is None or self.histograms is None:
            return

        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            return

        for channel_index, histogram in enumerate(self.histograms):
            maximum = histogram.max()
            if maximum == 0:
                continue

            scaled = histogram / maximum * max(height - 10, 1)
            painter.setPen(QPen([Qt.red, Qt.green, Qt.blue][channel_index]))
            previous = None
            for x in range(width):
                index = min(255, int(x / width * 256))
                y = height - int(scaled[index]) - 5
                if previous is not None:
                    painter.drawLine(previous[0], previous[1], x, y)
                previous = (x, y)
