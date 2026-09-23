from PIL.ImageQt import ImageQt

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget


class ImageCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.image = None
        self.before_image = None

        self.zoom = 1.0
        self.offset = QPoint(0, 0)

        self.dragging = False
        self.last_mouse_position = QPoint()

        self.show_before = False

        self.setMinimumSize(
            500,
            400
        )

        self.setMouseTracking(True)

    def set_image(self, image, before_image=None):
        self.image = image
        self.before_image = before_image

        self.fit_image()
        self.update()

    def fit_image(self):
        if self.image is None:
            return

        width = self.width()
        height = self.height()

        image_width = self.image.width
        image_height = self.image.height

        if image_width == 0 or image_height == 0:
            return

        zoom_x = width / image_width
        zoom_y = height / image_height

        self.zoom = min(
            zoom_x,
            zoom_y
        ) * 0.95

        self.offset = QPoint(
            width // 2,
            height // 2
        )

    def zoom_in(self):
        self.zoom *= 1.2
        self.update()

    def zoom_out(self):
        self.zoom /= 1.2
        self.update()

    def reset_view(self):
        self.fit_image()
        self.update()

    def toggle_before(self):
        self.show_before = not self.show_before
        self.update()

    def wheelEvent(self, event):
        if self.image is None:
            return

        delta = event.angleDelta().y()

        if delta > 0:
            self.zoom *= 1.15
        else:
            self.zoom /= 1.15

        self.zoom = max(
            0.02,
            min(
                self.zoom,
                20.0
            )
        )

        self.update()

    def mousePressEvent(self, event):
        if (
            event.button()
            == Qt.MiddleButton
        ):
            self.dragging = True
            self.last_mouse_position = (
                event.position().toPoint()
            )

            self.setCursor(
                Qt.ClosedHandCursor
            )

    def mouseMoveEvent(self, event):
        if not self.dragging:
            return

        current = event.position().toPoint()

        delta = (
            current
            - self.last_mouse_position
        )

        self.offset += delta

        self.last_mouse_position = current

        self.update()

    def mouseReleaseEvent(self, event):
        if (
            event.button()
            == Qt.MiddleButton
        ):
            self.dragging = False
            self.setCursor(
                Qt.ArrowCursor
            )

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.fillRect(
            self.rect(),
            Qt.black
        )

        if self.image is None:
            painter.setPen(
                Qt.white
            )

            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Open an image to begin"
            )

            return

        image = (
            self.before_image
            if self.show_before
            and self.before_image is not None
            else self.image
        )

        qt_image = ImageQt(image)

        pixmap = QPixmap.fromImage(
            qt_image
        )

        scaled_width = int(
            pixmap.width()
            * self.zoom
        )

        scaled_height = int(
            pixmap.height()
            * self.zoom
        )

        scaled = pixmap.scaled(
            scaled_width,
            scaled_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        x = (
            self.offset.x()
            - scaled.width() // 2
        )

        y = (
            self.offset.y()
            - scaled.height() // 2
        )

        painter.drawPixmap(
            x,
            y,
            scaled
        )