from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QVBoxLayout,
)

from ui.colour_wheel import ColourWheel
from ui.sliders import AdjustmentSlider


GRADES = [
    ("Shadows", "grading_shadows"),
    ("Midtones", "grading_midtones"),
    ("Highlights", "grading_highlights"),
    ("Global", "grading_global"),
]


class GradingPanel(QGroupBox):
    def __init__(
        self,
        document,
        on_change,
        parent=None
    ):
        super().__init__(
            "Colour Grading",
            parent
        )

        self.document = document
        self.on_change = on_change

        layout = QVBoxLayout(
            self
        )

        self.selector = QComboBox()

        for label, key in GRADES:
            self.selector.addItem(
                label,
                key
            )

        layout.addWidget(
            self.selector
        )

        self.wheel = ColourWheel(
            self.wheel_changed
        )

        layout.addWidget(
            self.wheel
        )

        self.luminance = AdjustmentSlider(
            "Luminance",
            -100,
            100,
            0
        )

        layout.addWidget(
            self.luminance
        )

        self.blending = AdjustmentSlider(
            "Blending",
            0,
            100,
            50
        )

        self.balance = AdjustmentSlider(
            "Balance",
            -100,
            100,
            0
        )

        layout.addWidget(
            self.blending
        )

        layout.addWidget(
            self.balance
        )

        self.selector.currentIndexChanged.connect(
            self.load_grade
        )

        self.luminance.valueChanged.connect(
            self.luminance_changed
        )

        self.blending.valueChanged.connect(
            lambda value:
            self.on_change(
                "grading_blending",
                value
            )
        )

        self.balance.valueChanged.connect(
            lambda value:
            self.on_change(
                "grading_balance",
                value
            )
        )

        self.load_grade()

    def current_key(self):
        return self.selector.currentData()

    def load_grade(self):
        key = self.current_key()

        grade = getattr(
            self.document.adjustments,
            key
        )

        self.wheel.hue = grade[
            "hue"
        ]

        self.wheel.saturation = grade[
            "saturation"
        ]

        self.wheel.update()

        self.luminance.blockSignals(True)

        self.luminance.setValue(
            grade["luminance"]
        )

        self.luminance.blockSignals(False)

    def wheel_changed(
        self,
        hue,
        saturation
    ):
        key = self.current_key()

        self.on_change(
            key,
            {
                "hue": hue,
                "saturation": saturation,
                "luminance": self.luminance.value(),
            }
        )

    def luminance_changed(
        self,
        value
    ):
        key = self.current_key()

        self.on_change(
            key,
            {
                "hue": self.wheel.hue,
                "saturation": self.wheel.saturation,
                "luminance": value,
            }
        )