import sys

from PySide6.QtWidgets import QApplication

from app.application import PhotoEditorApplication


def main():
    app = QApplication(sys.argv)

    editor = PhotoEditorApplication()
    editor.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()