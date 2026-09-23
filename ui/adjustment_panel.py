from PySide6.QtWidgets import (
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.sliders import AdjustmentSlider
from ui.hsl_panel import HSLPanel
from ui.curves_widget import CurvesPanel
from ui.grading_panel import GradingPanel


class AdjustmentPanel(QWidget):
    def __init__(
        self,
        document,
        on_change,
        parent=None
    ):
        super().__init__(parent)

        self.document = document
        self.on_change = on_change

        layout = QVBoxLayout(
            self
        )

        self.tabs = QTabWidget()

        layout.addWidget(
            self.tabs
        )

        self.create_basic_tab()

        self.hsl_panel = HSLPanel(
            document,
            on_change
        )

        self.tabs.addTab(
            self.hsl_panel,
            "HSL"
        )

        self.curves_panel = CurvesPanel(
            document,
            self.curves_changed
        )

        self.tabs.addTab(
            self.curves_panel,
            "Curves"
        )

        self.grading_panel = GradingPanel(
            document,
            self.grading_changed
        )

        self.tabs.addTab(
            self.grading_panel,
            "Grading"
        )

    def create_basic_tab(self):
        widget = QWidget()

        layout = QVBoxLayout(
            widget
        )

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

        self.basic_sliders = {}

        for label, name, minimum, maximum in definitions:
            slider = AdjustmentSlider(
                label,
                minimum,
                maximum,
                0
            )

            slider.valueChanged.connect(
                lambda value, key=name:
                self.basic_changed(
                    key,
                    value
                )
            )

            self.basic_sliders[
                name
            ] = slider

            layout.addWidget(
                slider
            )

        layout.addStretch()

        self.tabs.addTab(
            widget,
            "Basic"
        )

    def basic_changed(
        self,
        name,
        value
    ):
        self.on_change(
            name,
            value
        )

    def curves_changed(
        self,
        channel,
        points
    ):
        self.on_change(
            f"curves_{channel}",
            points
        )

    def grading_changed(
        self,
        key,
        value
    ):
        self.on_change(
            key,
            value
        )

    def refresh(self):
        adjustments = self.document.adjustments

        for name, slider in self.basic_sliders.items():
            slider.blockSignals(True)

            slider.setValue(
                getattr(
                    adjustments,
                    name
                )
            )

            slider.blockSignals(False)

        self.hsl_panel.load_channel()
        self.grading_panel.load_grade()
        self.curves_panel.curves.load_points()
        self.curves_panel.curves.update()