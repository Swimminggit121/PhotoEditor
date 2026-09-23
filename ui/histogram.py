import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QWidget


class HistogramWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.image = None

        self.setMinimumHeight(150)

    def set_image(self, image):
        self.image = image
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.fillRect(
            self.rect(),
            Qt.black
        )

        if self.image is None:
            return

        array = np.asarray(
            self.image
        )

        channels = [
            array[..., 0],
            array[..., 1],
            array[..., 2],
        ]

        width = self.width()
        height = self.height()

        for channel_index, channel in enumerate(channels):
            histogram, _ = np.histogram(
                channel,
                bins=256,
                range=(0, 255)
            )

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

            previous = None

            for x in range(width):
                index = int(
                    x / width * 255
                )

                y = height - int(
                    histogram[index]
                ) - 5

                if previous is not None:
                    painter.drawLine(
                        previous[0],
                        previous[1],
                        x,
                        y
                    )

                previous = (
                    x,
                    y
                )