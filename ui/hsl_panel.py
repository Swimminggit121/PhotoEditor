from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QComboBox,
    QLabel,
)

from ui.sliders import AdjustmentSlider


CHANNELS = [
    "Red",
    "Orange",
    "Yellow",
    "Green",
    "Aqua",
    "Blue",
    "Purple",
    "Magenta",
]


class HSLPanel(QGroupBox):
    def __init__(
        self,
        document,
        on_change,
        parent=None
    ):
        super().__init__(
            "HSL / Colour Mixer",
            parent
        )

        self.document = document
        self.on_change = on_change

        layout = QVBoxLayout(
            self
        )

        self.channel_selector = (
            QComboBox()
        )

        self.channel_selector.addItems(
            CHANNELS
        )

        layout.addWidget(
            self.channel_selector
        )

        self.hue = AdjustmentSlider(
            "Hue",
            -100,
            100,
            0
        )

        self.saturation = AdjustmentSlider(
            "Saturation",
            -100,
            100,
            0
        )

        self.luminance = AdjustmentSlider(
            "Luminance",
            -100,
            100,
            0
        )

        layout.addWidget(
            self.hue
        )

        layout.addWidget(
            self.saturation
        )

        layout.addWidget(
            self.luminance
        )

        self.channel_selector.currentIndexChanged.connect(
            self.load_channel
        )

        self.hue.valueChanged.connect(
            self.changed
        )

        self.saturation.valueChanged.connect(
            self.changed
        )

        self.luminance.valueChanged.connect(
            self.changed
        )

        self.load_channel()

    def current_channel(self):
        return self.channel_selector.currentText().lower()

    def load_channel(self):
        channel = self.current_channel()

        values = self.document.adjustments.hsl[
            channel
        ]

        self.hue.blockSignals(True)
        self.saturation.blockSignals(True)
        self.luminance.blockSignals(True)

        self.hue.setValue(
            values["hue"]
        )

        self.saturation.setValue(
            values["saturation"]
        )

        self.luminance.setValue(
            values["luminance"]
        )

        self.hue.blockSignals(False)
        self.saturation.blockSignals(False)
        self.luminance.blockSignals(False)

    def changed(self):
        channel = self.current_channel()

        self.on_change(
            "hsl",
            channel,
            {
                "hue": self.hue.value(),
                "saturation": self.saturation.value(),
                "luminance": self.luminance.value(),
            }
        )