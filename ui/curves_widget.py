from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QBrush,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QVBoxLayout,
    QWidget,
)


class CurvesWidget(QWidget):
    def __init__(
        self,
        document,
        on_change,
        parent=None
    ):
        super().__init__(parent)

        self.document = document
        self.on_change = on_change

        self.channel = "master"

        self.points = [
            (0.0, 0.0),
            (1.0, 1.0),
        ]

        self.dragging = None

        self.setMinimumHeight(
            260
        )

        self.setMinimumWidth(
            300
        )

    def set_channel(self, channel):
        self.channel = channel

        self.load_points()

        self.update()

    def load_points(self):
        attribute = (
            f"curves_{self.channel}"
        )

        self.points = [
            tuple(point)
            for point in getattr(
                self.document.adjustments,
                attribute
            )
        ]

    def paintEvent(self, event):
        painter = QPainter(
            self
        )

        painter.fillRect(
            self.rect(),
            Qt.black
        )

        width = self.width()
        height = self.height()

        painter.setPen(
            QPen(
                Qt.darkGray,
                1
            )
        )

        for i in range(1, 4):
            x = int(
                width * i / 4
            )

            y = int(
                height * i / 4
            )

            painter.drawLine(
                x,
                0,
                x,
                height
            )

            painter.drawLine(
                0,
                y,
                width,
                y
            )

        painter.setPen(
            QPen(
                Qt.gray,
                2
            )
        )

        previous = None

        for i in range(width):
            value = i / max(
                width - 1,
                1
            )

            output = self.interpolate(
                value
            )

            x = i
            y = int(
                (1.0 - output)
                * height
            )

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

        painter.setBrush(
            QBrush(
                Qt.white
            )
        )

        painter.setPen(
            QPen(
                Qt.black,
                1
            )
        )

        for x_value, y_value in self.points:
            x = int(
                x_value
                * width
            )

            y = int(
                (1.0 - y_value)
                * height
            )

            painter.drawEllipse(
                x - 6,
                y - 6,
                12,
                12
            )

    def interpolate(self, value):
        points = sorted(
            self.points
        )

        if value <= points[0][0]:
            return points[0][1]

        if value >= points[-1][0]:
            return points[-1][1]

        for index in range(
            len(points) - 1
        ):
            x1, y1 = points[index]
            x2, y2 = points[index + 1]

            if x1 <= value <= x2:
                amount = (
                    value - x1
                ) / (
                    x2 - x1
                )

                return (
                    y1
                    + (
                        y2 - y1
                    )
                    * amount
                )

        return value

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        x = event.position().x()
        y = event.position().y()

        x_value = (
            x / max(
                self.width(),
                1
            )
        )

        y_value = 1.0 - (
            y / max(
                self.height(),
                1
            )
        )

        x_value = max(
            0.0,
            min(
                1.0,
                x_value
            )
        )

        y_value = max(
            0.0,
            min(
                1.0,
                y_value
            )
        )

        nearest = None
        distance = 999

        for index, point in enumerate(
            self.points
        ):
            px = point[0] * self.width()
            py = (
                1.0 - point[1]
            ) * self.height()

            d = (
                (px - x) ** 2
                + (py - y) ** 2
            )

            if d < distance:
                distance = d
                nearest = index

        if distance < 15 ** 2:
            self.dragging = nearest

        else:
            self.points.append(
                (
                    x_value,
                    y_value
                )
            )

            self.points.sort()

            self.on_change(
                self.channel,
                self.points
            )

            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging is None:
            return

        x_value = (
            event.position().x()
            / max(
                self.width(),
                1
            )
        )

        y_value = 1.0 - (
            event.position().y()
            / max(
                self.height(),
                1
            )
        )

        x_value = max(
            0.0,
            min(
                1.0,
                x_value
            )
        )

        y_value = max(
            0.0,
            min(
                1.0,
                y_value
            )
        )

        self.points[
            self.dragging
        ] = (
            x_value,
            y_value
        )

        self.points.sort()

        self.on_change(
            self.channel,
            self.points
        )

        self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = None


class CurvesPanel(QGroupBox):
    def __init__(
        self,
        document,
        on_change,
        parent=None
    ):
        super().__init__(
            "Curves",
            parent
        )

        self.document = document
        self.on_change = on_change

        layout = QVBoxLayout(
            self
        )

        self.selector = QComboBox()

        self.selector.addItem(
            "RGB",
            "master"
        )

        self.selector.addItem(
            "Red",
            "red"
        )

        self.selector.addItem(
            "Green",
            "green"
        )

        self.selector.addItem(
            "Blue",
            "blue"
        )

        layout.addWidget(
            self.selector
        )

        self.curves = CurvesWidget(
            document,
            on_change
        )

        layout.addWidget(
            self.curves
        )

        self.selector.currentIndexChanged.connect(
            self.channel_changed
        )

    def channel_changed(self):
        self.curves.set_channel(
            self.selector.currentData()
        )