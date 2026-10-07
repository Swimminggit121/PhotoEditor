import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget


class ColourWheel(QWidget):
    def __init__(
        self,
        on_change=None,
        parent=None
    ):
        super().__init__(parent)

        self.hue = 0.0
        self.saturation = 0.0

        self.on_change = on_change
        self._wheel_pixmap = None

        self.setMinimumSize(
            160,
            160
        )

    def paintEvent(self, event):
        size = self.size()
        if self._wheel_pixmap is None or self._wheel_pixmap.size() != size:
            self._wheel_pixmap = QPixmap(size)
            self._wheel_pixmap.fill(Qt.transparent)
            wheel_painter = QPainter(self._wheel_pixmap)
            wheel_painter.setRenderHint(QPainter.Antialiasing)
            centre = QPointF(self.width() / 2, self.height() / 2)
            radius = min(self.width(), self.height()) / 2 - 10
            for angle in range(360):
                wheel_painter.setPen(QPen(QColor.fromHsv(angle, 255, 255), 3))
                radians = math.radians(angle)
                inner = QPointF(
                    centre.x() + math.cos(radians) * radius * 0.35,
                    centre.y() + math.sin(radians) * radius * 0.35,
                )
                outer = QPointF(
                    centre.x() + math.cos(radians) * radius,
                    centre.y() + math.sin(radians) * radius,
                )
                wheel_painter.drawLine(inner, outer)
            wheel_painter.setBrush(QBrush(QColor(40, 40, 40)))

            wheel_painter.setPen(Qt.NoPen)
            wheel_painter.drawEllipse(centre, radius * 0.35, radius * 0.35)
            wheel_painter.end()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(0, 0, self._wheel_pixmap)
        centre = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 10

        radians = math.radians(
            self.hue
        )

        marker_radius = (
            radius
            * (
                0.35
                + self.saturation
                / 100.0
                * 0.65
            )
        )

        marker = QPointF(
            centre.x()
            + math.cos(radians)
            * marker_radius,

            centre.y()
            + math.sin(radians)
            * marker_radius
        )

        painter.setPen(
            QPen(
                Qt.white,
                3
            )
        )

        painter.setBrush(
            Qt.NoBrush
        )

        painter.drawEllipse(
            marker,
            7,
            7
        )

    def mousePressEvent(self, event):
        self.update_from_position(
            event.position()
        )

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.update_from_position(
                event.position()
            )

    def update_from_position(
        self,
        position
    ):
        cx = self.width() / 2
        cy = self.height() / 2

        dx = position.x() - cx
        dy = position.y() - cy

        distance = math.sqrt(
            dx * dx
            + dy * dy
        )

        radius = min(
            self.width(),
            self.height()
        ) / 2 - 10

        saturation = (
            (distance - radius * 0.35)
            / (radius * 0.65)
            * 100
        )

        saturation = max(
            0.0,
            min(
                100.0,
                saturation
            )
        )

        hue = math.degrees(
            math.atan2(
                dy,
                dx
            )
        )

        if hue < 0:
            hue += 360

        self.hue = hue
        self.saturation = saturation

        self.update()

        if self.on_change:
            self.on_change(
                self.hue,
                self.saturation
            )