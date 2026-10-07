import numpy as np

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget


class HistogramWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.image = None
        self.histograms = None

        self.setMinimumHeight(150)

    def set_image(self, image):
        if image is self.image:return
        self.image = image
        if image is None:
            self.histograms = None
        else:
            array = np.asarray(image.convert('RGB'), dtype=np.uint8)
            self.histograms = [np.histogram(channel, bins=256, range=(0, 255))[0] for channel in (array[...,0], array[...,1], array[...,2])]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.fillRect(
            self.rect(),
            Qt.black
        )

        if self.image is None:
            return

        if self.histograms is None:
            return

        width = self.width()
        height = self.height()

        for channel_index, histogram in enumerate(self.histograms):
            if histogram.max() == 0:
                continue

            histogram = (
                histogram
                / histogram.max()
                * (height - 10)
            )

            pen = QPen(
                [
                    Qt.red,
                    Qt.green,
                    Qt.blue,
                ][channel_index]
            )

            painter.setPen(pen)

            points = QPolygonF()
            for x, value in enumerate(histogram):
                px = x / 255 * max(0, width - 1)
                py = height - int(value) - 5
                points.append(QPointF(px, py))
            painter.drawPolyline(points)