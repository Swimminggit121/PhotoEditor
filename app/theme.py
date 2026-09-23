from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt


def apply_theme(app):
    palette = QPalette()

    palette.setColor(QPalette.Window, QColor("#1b1b1b"))
    palette.setColor(QPalette.WindowText, QColor("#eeeeee"))
    palette.setColor(QPalette.Base, QColor("#121212"))
    palette.setColor(QPalette.AlternateBase, QColor("#202020"))
    palette.setColor(QPalette.ToolTipBase, QColor("#202020"))
    palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
    palette.setColor(QPalette.Text, QColor("#eeeeee"))
    palette.setColor(QPalette.Button, QColor("#252525"))
    palette.setColor(QPalette.ButtonText, QColor("#eeeeee"))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Highlight, QColor("#4b78d1"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))

    app.setPalette(palette)

    app.setStyleSheet(
        """
        QWidget {
            background-color: #1b1b1b;
            color: #eeeeee;
            font-family: "Segoe UI";
            font-size: 10pt;
        }

        QMainWindow {
            background-color: #151515;
        }

        QMenuBar {
            background-color: #181818;
            border-bottom: 1px solid #303030;
            padding: 3px;
        }

        QMenuBar::item {
            padding: 6px 10px;
            background: transparent;
        }

        QMenuBar::item:selected {
            background-color: #303030;
        }

        QMenu {
            background-color: #222222;
            border: 1px solid #3a3a3a;
        }

        QMenu::item {
            padding: 7px 30px 7px 15px;
        }

        QMenu::item:selected {
            background-color: #3c5f9e;
        }

        QToolBar {
            background-color: #181818;
            border: none;
            spacing: 4px;
            padding: 4px;
        }

        QToolButton {
            background-color: transparent;
            border: 1px solid transparent;
            padding: 6px;
            border-radius: 4px;
        }

        QToolButton:hover {
            background-color: #303030;
        }

        QToolButton:checked {
            background-color: #3c5f9e;
        }

        QDockWidget {
            titlebar-close-icon: none;
            titlebar-normal-icon: none;
        }

        QDockWidget::title {
            background-color: #202020;
            padding: 8px;
            text-align: left;
            font-weight: bold;
        }

        QSlider::groove:horizontal {
            height: 4px;
            background: #444444;
            border-radius: 2px;
        }

        QSlider::handle:horizontal {
            width: 12px;
            height: 12px;
            margin: -5px 0;
            background: #dddddd;
            border-radius: 6px;
        }

        QSlider::handle:horizontal:hover {
            background: #ffffff;
        }

        QPushButton {
            background-color: #292929;
            border: 1px solid #404040;
            border-radius: 4px;
            padding: 6px 12px;
        }

        QPushButton:hover {
            background-color: #353535;
        }

        QPushButton:pressed {
            background-color: #414141;
        }

        QStatusBar {
            background-color: #181818;
            border-top: 1px solid #303030;
        }
        """
    )

    app.setAttribute(Qt.AA_UseHighDpiPixmaps)