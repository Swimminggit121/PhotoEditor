from PySide6.QtWidgets import QApplication
from app.theme import apply_theme
from video.editor import VideoEditorWindow
class VideoEditorApplication:
    def __init__(self):
        self.app=QApplication.instance();apply_theme(self.app);self.window=VideoEditorWindow()
    def show(self):
        self.window.show();self.window.raise_();self.window.activateWindow()
