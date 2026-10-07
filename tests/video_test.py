import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication
from app.window import MainWindow
from suite_main import SuiteWindow
from video.editor import VideoEditorWindow


def main():
    app = QApplication.instance() or QApplication([])
    photo = MainWindow()
    video = VideoEditorWindow()
    suite = SuiteWindow()

    assert photo.windowTitle().startswith("PhotoEditor")
    assert video.windowTitle().startswith("Video")
    assert suite.windowTitle() == "PhotoEditor Suite"
    assert suite.centralWidget() is not None
    assert suite.centralWidget().count() == 2

    suite.close()
    video.close()
    photo.close()
    app.quit()
    print("VIDEO + SUITE UI TEST OK")


if __name__ == "__main__":
    main()
