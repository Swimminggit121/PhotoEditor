from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolBar


class MainToolBar(QToolBar):
    def __init__(self, window):
        super().__init__(
            "Main Toolbar",
            window
        )

        self.setMovable(False)

        open_action = QAction(
            "Open",
            self
        )
        open_action.triggered.connect(
            window.open_image
        )

        self.addAction(
            open_action
        )

        self.addSeparator()

        zoom_in = QAction(
            "Zoom +",
            self
        )
        zoom_in.triggered.connect(
            window.zoom_in
        )

        self.addAction(
            zoom_in
        )

        zoom_out = QAction(
            "Zoom -",
            self
        )
        zoom_out.triggered.connect(
            window.zoom_out
        )

        self.addAction(
            zoom_out
        )

        fit = QAction(
            "Fit",
            self
        )
        fit.triggered.connect(
            window.fit_image
        )

        self.addAction(
            fit
        )

        self.addSeparator()

        before = QAction(
            "Before / After",
            self
        )
        before.setCheckable(True)
        before.triggered.connect(
            window.toggle_before
        )

        self.addAction(
            before
        )