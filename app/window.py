from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
)

from core.document import Document
from image.export import export_image

from ui.adjustment_panel import AdjustmentPanel
from ui.canvas import ImageCanvas
from ui.histogram import HistogramWidget
from ui.menu_bar import MenuBar
from ui.toolbar import MainToolBar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.document = Document()

        self.setWindowTitle(
            "PhotoEditor"
        )

        self.resize(
            1500,
            900
        )

        self.setMinimumSize(
            1100,
            700
        )

        self.canvas = ImageCanvas()

        self.setCentralWidget(
            self.canvas
        )

        self.create_menu()
        self.create_toolbar()
        self.create_adjustment_panel()
        self.create_histogram()
        self.create_status_bar()

        self.update_title()

    def create_menu(self):
        self.setMenuBar(
            MenuBar(self)
        )

    def create_toolbar(self):
        toolbar = MainToolBar(
            self
        )

        self.addToolBar(
            Qt.TopToolBarArea,
            toolbar
        )

    def create_adjustment_panel(self):
        self.adjustment_panel = (
            AdjustmentPanel(
                self.document,
                self.change_adjustment
            )
        )

        dock = QDockWidget(
            "Develop",
            self
        )

        dock.setWidget(
            self.adjustment_panel
        )

        dock.setAllowedAreas(
            Qt.RightDockWidgetArea
        )

        dock.setMinimumWidth(
            380
        )

        self.addDockWidget(
            Qt.RightDockWidgetArea,
            dock
        )

    def create_histogram(self):
        self.histogram = HistogramWidget()

        dock = QDockWidget(
            "Histogram",
            self
        )

        dock.setWidget(
            self.histogram
        )

        dock.setAllowedAreas(
            Qt.RightDockWidgetArea
        )

        dock.setMinimumHeight(
            190
        )

        self.addDockWidget(
            Qt.RightDockWidgetArea,
            dock
        )

    def create_status_bar(self):
        self.status_label = QLabel(
            "Ready"
        )

        self.statusBar().addPermanentWidget(
            self.status_label
        )

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            (
                "Images (*.jpg *.jpeg *.png *.tif "
                "*.tiff *.webp *.bmp);;"
                "All Files (*)"
            )
        )

        if not path:
            return

        try:
            self.document.load(path)

            self.refresh_view()

            self.status_label.setText(
                f"Opened: {Path(path).name}"
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Could not open image",
                str(exc)
            )

    def change_adjustment(
        self,
        *args
    ):
        if not args:
            return

        if len(args) == 2:
            name, value = args

            if name.startswith(
                "curves_"
            ):
                setattr(
                    self.document.adjustments,
                    name,
                    value
                )

            elif isinstance(
                value,
                dict
            ):
                setattr(
                    self.document.adjustments,
                    name,
                    value
                )

            else:
                setattr(
                    self.document.adjustments,
                    name,
                    float(value)
                )

        elif len(args) == 3:
            name, channel, values = args

            self.document.adjustments.hsl[
                channel
            ] = values

        self.document.dirty = True

        self.refresh_render()

    def refresh_render(self):
        if not self.document.has_image():
            return

        rendered = self.document.render()

        self.canvas.set_image(
            rendered,
            self.document.original_image
        )

        self.histogram.set_image(
            rendered
        )

        self.update_title()

    def refresh_view(self):
        if not self.document.has_image():
            return

        rendered = self.document.render()

        self.canvas.set_image(
            rendered,
            self.document.original_image
        )

        self.histogram.set_image(
            rendered
        )

        self.adjustment_panel.refresh()

        self.update_title()

    def undo(self):
        if self.document.undo():
            self.refresh_view()

    def redo(self):
        if self.document.redo():
            self.refresh_view()

    def reset_adjustments(self):
        if not self.document.has_image():
            return

        self.document.reset_adjustments()

        self.refresh_view()

    def zoom_in(self):
        self.canvas.zoom_in()

    def zoom_out(self):
        self.canvas.zoom_out()

    def fit_image(self):
        self.canvas.reset_view()

    def toggle_before(self):
        self.canvas.toggle_before()

    def export_image(self):
        if not self.document.has_image():
            QMessageBox.information(
                self,
                "Export",
                "Open an image first."
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Image",
            "",
            (
                "JPEG (*.jpg *.jpeg);;"
                "PNG (*.png);;"
                "TIFF (*.tif *.tiff);;"
                "WebP (*.webp)"
            )
        )

        if not path:
            return

        try:
            image = self.document.render()

            export_image(
                image,
                path
            )

            self.status_label.setText(
                f"Exported: {Path(path).name}"
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Export failed",
                str(exc)
            )

    def save_project(self):
        QMessageBox.information(
            self,
            "PhotoEditor Project",
            "Full project saving will be added in the project system."
        )

    def update_title(self):
        if self.document.path:
            marker = (
                " *"
                if self.document.dirty
                else ""
            )

            self.setWindowTitle(
                "PhotoEditor — "
                f"{self.document.path.name}"
                f"{marker}"
            )

        else:
            self.setWindowTitle(
                "PhotoEditor"
            )

    def closeEvent(self, event):
        if self.document.dirty:
            result = QMessageBox.question(
                self,
                "Unsaved Changes",
                (
                    "You have unsaved changes. "
                    "Are you sure you want to exit?"
                ),
                QMessageBox.Yes
                | QMessageBox.No
            )

            if result != QMessageBox.Yes:
                event.ignore()
                return

        event.accept()