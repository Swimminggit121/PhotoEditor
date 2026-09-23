from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar


class MenuBar(QMenuBar):
    def __init__(self, window):
        super().__init__(window)

        file_menu = self.addMenu("File")

        open_action = QAction(
            "Open...",
            self
        )
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(
            window.open_image
        )

        file_menu.addAction(
            open_action
        )

        export_action = QAction(
            "Export...",
            self
        )
        export_action.setShortcut("Ctrl+Shift+S")
        export_action.triggered.connect(
            window.export_image
        )

        file_menu.addAction(
            export_action
        )

        file_menu.addSeparator()

        save_project = QAction(
            "Save Project",
            self
        )
        save_project.setShortcut(
            "Ctrl+S"
        )
        save_project.triggered.connect(
            window.save_project
        )

        file_menu.addAction(
            save_project
        )

        file_menu.addSeparator()

        exit_action = QAction(
            "Exit",
            self
        )
        exit_action.setShortcut(
            "Ctrl+Q"
        )
        exit_action.triggered.connect(
            window.close
        )

        file_menu.addAction(
            exit_action
        )

        edit_menu = self.addMenu("Edit")

        undo_action = QAction(
            "Undo",
            self
        )
        undo_action.setShortcut(
            "Ctrl+Z"
        )
        undo_action.triggered.connect(
            window.undo
        )

        edit_menu.addAction(
            undo_action
        )

        redo_action = QAction(
            "Redo",
            self
        )
        redo_action.setShortcut(
            "Ctrl+Y"
        )
        redo_action.triggered.connect(
            window.redo
        )

        edit_menu.addAction(
            redo_action
        )

        edit_menu.addSeparator()

        reset_action = QAction(
            "Reset Adjustments",
            self
        )

        reset_action.triggered.connect(
            window.reset_adjustments
        )

        edit_menu.addAction(
            reset_action
        )

        view_menu = self.addMenu("View")

        zoom_in = QAction(
            "Zoom In",
            self
        )
        zoom_in.setShortcut(
            "+"
        )
        zoom_in.triggered.connect(
            window.zoom_in
        )

        view_menu.addAction(
            zoom_in
        )

        zoom_out = QAction(
            "Zoom Out",
            self
        )
        zoom_out.setShortcut(
            "-"
        )
        zoom_out.triggered.connect(
            window.zoom_out
        )

        view_menu.addAction(
            zoom_out
        )

        fit = QAction(
            "Fit Image",
            self
        )
        fit.setShortcut(
            "F"
        )
        fit.triggered.connect(
            window.fit_image
        )

        view_menu.addAction(
            fit
        )

        before_after = QAction(
            "Before / After",
            self
        )
        before_after.setShortcut(
            "B"
        )
        before_after.triggered.connect(
            window.toggle_before
        )

        view_menu.addAction(
            before_after
        )