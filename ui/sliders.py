from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSlider,
    QWidget,
)


class AdjustmentSlider(QWidget):
    valueChanged = Signal(float)

    def __init__(
        self,
        name,
        minimum=-100,
        maximum=100,
        value=0,
        decimals=0,
        parent=None,
    ):
        super().__init__(parent)

        self.decimals = decimals

        self.label = QLabel(name)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(
            minimum,
            maximum
        )

        self.slider.setValue(
            int(value)
        )

        self.value_label = QLabel(
            self.format_value(value)
        )

        self.value_label.setMinimumWidth(45)
        self.value_label.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            8,
            3,
            8,
            3
        )

        layout.addWidget(
            self.label,
            0
        )

        layout.addWidget(
            self.slider,
            1
        )

        layout.addWidget(
            self.value_label,
            0
        )

        self.slider.valueChanged.connect(
            self._changed
        )

    def format_value(self, value):
        if self.decimals == 0:
            return f"{int(value):+d}"

        return f"{value:+.{self.decimals}f}"

    def _changed(self, value):
        self.value_label.setText(
            self.format_value(value)
        )

        self.valueChanged.emit(
            float(value)
        )

    def setValue(self, value):
        self.slider.setValue(
            int(round(value))
        )

    def value(self):
        return float(
            self.slider.value()
        )