from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QWidget,
)

from ui.sliders import AdjustmentSlider


class AdjustmentPanel(QWidget):
    def __init__(self, document, on_change, parent=None):
        super().__init__(parent)

        self.document = document
        self.on_change = on_change

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            4,
            4,
            4,
            4
        )

        basic = QGroupBox("Basic")

        basic_layout = QVBoxLayout(
            basic
        )

        self.sliders = {}

        definitions = [
            ("Exposure", "exposure", -50, 50),
            ("Contrast", "contrast", -100, 100),
            ("Highlights", "highlights", -100, 100),
            ("Shadows", "shadows", -100, 100),
            ("Whites", "whites", -100, 100),
            ("Blacks", "blacks", -100, 100),
            ("Temperature", "temperature", -100, 100),
            ("Tint", "tint", -100, 100),
            ("Saturation", "saturation", -100, 100),
            ("Vibrance", "vibrance", -100, 100),
        ]

        for label, name, minimum, maximum in definitions:
            slider = AdjustmentSlider(
                label,
                minimum,
                maximum,
                0
            )

            slider.valueChanged.connect(
                lambda value, key=name:
                self._adjustment_changed(
                    key,
                    value
                )
            )

            self.sliders[name] = slider
            basic_layout.addWidget(slider)

        layout.addWidget(basic)

        layout.addStretch()

    def _adjustment_changed(self, name, value):
        self.on_change(
            name,
            value
        )

    def refresh(self):
        adjustments = self.document.adjustments

        for name, slider in self.sliders.items():
            value = getattr(
                adjustments,
                name
            )

            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)