from PySide6.QtWidgets import QApplication

from app.theme import apply_theme
from app.window import MainWindow


class PhotoEditorApplication:
    def __init__(self):
        self.app = QApplication.instance()

        apply_theme(self.app)

        self.window = MainWindow()

    def show(self):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()