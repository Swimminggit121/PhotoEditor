# THESIS: One creative suite, two focused workspaces; it refuses to bury editing modes in feature menus.
# OWN-WORLD: Segoe UI, graphite surfaces, quiet separators, precise blue for active choices, native controls.
# STORY: Users see what each editor does, choose one, and can return to switch workspaces without losing projects.
# FIRST VIEWPORT: A compact title, a two-column photo/video choice, and one explicit Open Workspace action per column.
# FORM: A native desktop workspace chooser extending PhotoEditor's existing restrained dark interface.

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.window import MainWindow
from ui.video_editor_window import VideoEditorWindow
from ui.photo_catalog_window import PhotoCatalogWindow


class WorkspaceLauncher(QMainWindow):
    def __init__(self, allowed_modes=None):
        super().__init__()
        self.setWindowTitle("PhotoEditor — Choose a Workspace")
        self.setMinimumSize(760, 470)
        self.resize(900, 540)
        self.allowed_modes = set(allowed_modes or {"photo", "video"})
        self.suite_mode = {"photo", "video"}.issubset(self.allowed_modes)
        self._editors = {}
        self._catalog_window = None

        heading = QLabel("Choose a workspace")
        heading.setStyleSheet("font-size: 22pt; font-weight: 600;")
        intro = QLabel("Open the tools for the work you want to do. Projects stay separate and editable.")
        intro.setWordWrap(True)
        self.catalog_action = QPushButton("Open Photo Catalog")
        self.catalog_action.setToolTip("Search shoots, review local quality hints, rate and flag photos, and export edited copies.")
        self.catalog_action.clicked.connect(self.open_catalog)
        if "photo" not in self.allowed_modes:
            self.catalog_action.hide()

        self.photo_action = QPushButton("Open Photo Editor")
        self.video_action = QPushButton("Open Video Editor")
        columns = QHBoxLayout()
        columns.setSpacing(22)
        if "photo" in self.allowed_modes:
            columns.addWidget(self._workspace(
                "Photo Editor",
                "Develop RAW and standard photos with non-destructive adjustments, masks, batch editing, "
                "presets, and full-resolution 1:1 inspection.",
                self.photo_action,
            ), 1)
        else:
            self.photo_action.hide()
        if "photo" in self.allowed_modes and "video" in self.allowed_modes:
            divider = QWidget()
            divider.setFixedWidth(1)
            divider.setStyleSheet("background-color: #343434;")
            columns.addWidget(divider)
        if "video" in self.allowed_modes:
            columns.addWidget(self._workspace(
                "Video Editor",
                "Build a multitrack sequence from photos, video, music, and sound effects; trim and split clips, "
                "preview the sequence, and export H.264 MP4.",
                self.video_action,
            ), 1)
        else:
            self.video_action.hide()

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.addWidget(heading)
        layout.addWidget(intro)
        layout.addWidget(self.catalog_action, 0, Qt.AlignLeft)
        layout.addSpacing(12)
        layout.addLayout(columns, 1)
        self.setCentralWidget(root)

        self.photo_action.clicked.connect(lambda: self.open_workspace("photo"))
        self.video_action.clicked.connect(lambda: self.open_workspace("video"))

    @staticmethod
    def _workspace(title, description, button):
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 18, 18, 18)
        label = QLabel(title)
        label.setStyleSheet("font-size: 16pt; font-weight: 600;")
        copy = QLabel(description)
        copy.setWordWrap(True)
        copy.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(label)
        layout.addWidget(copy, 1)
        layout.addWidget(button)
        return section

    def open_workspace(self, mode):
        if mode not in self.allowed_modes:
            raise ValueError(f"The {mode} workspace is not included in this application edition.")
        editor = self._editors.get(mode)
        if editor is None:
            if mode == "photo":
                editor = MainWindow(
                    on_home=self.show_hub,
                    on_catalog=self.open_catalog,
                    suite_mode=self.suite_mode,
                )
            elif mode == "video":
                editor = VideoEditorWindow(on_home=self.show_hub, suite_mode=self.suite_mode)
            else:
                raise ValueError(f"Unknown workspace: {mode}")
            self._editors[mode] = editor
        self.hide()
        editor.show()
        editor.raise_()
        editor.activateWindow()

    def open_catalog(self):
        if "photo" not in self.allowed_modes:
            raise ValueError("The photo catalog is not included in this application edition.")
        if self._catalog_window is None:
            self._catalog_window = PhotoCatalogWindow()
            self._catalog_window.photo_selected.connect(self._open_photo_from_catalog)
            self._catalog_window.photo_workspace_requested.connect(
                lambda: self._show_photo_editor()
            )
            self._catalog_window.video_requested.connect(self._create_video_from_catalog)
        self.hide()
        self._catalog_window.show()
        self._catalog_window.raise_()
        self._catalog_window.activateWindow()

    def _show_photo_editor(self):
        self.open_workspace("photo")
        if self._catalog_window:
            self._catalog_window.hide()

    def _open_photo_from_catalog(self, path):
        editor = self._editors.get("photo")
        if editor is None:
            editor = MainWindow(
                on_home=self.show_hub,
                on_catalog=self.open_catalog,
                suite_mode=self.suite_mode,
            )
            self._editors["photo"] = editor
        if editor.open_image_path(path):
            if self._catalog_window:
                self._catalog_window.hide()
            self.hide()
            editor.show()
            editor.raise_()
            editor.activateWindow()

    def _create_video_from_catalog(self, paths):
        editor = self._editors.get("photo")
        if editor is None:
            editor = MainWindow(
                on_home=self.show_hub,
                on_catalog=self.open_catalog,
                suite_mode=self.suite_mode,
            )
            self._editors["photo"] = editor
        if self._catalog_window:
            self._catalog_window.hide()
        self.hide()
        editor.show()
        editor.raise_()
        editor.activateWindow()
        editor.create_video_montage(initial_paths=paths)

    def show_hub(self):
        for editor in self._editors.values():
            editor.hide()
        if self._catalog_window:
            self._catalog_window.hide()
        self.show()
        self.raise_()
        self.activateWindow()
