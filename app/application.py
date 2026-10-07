import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.theme import apply_theme
from ui.workspace_launcher import WorkspaceLauncher


class PhotoEditorApplication:
    def __init__(self):
        self.app = QApplication.instance()

        apply_theme(self.app)
        name = Path(sys.executable).stem.casefold()
        self.mode = (
            "photo" if name == "photoeditor-photo"
            else "video" if name == "photoeditor-video"
            else next(
                (sys.argv[index + 1].casefold() for index, arg in enumerate(sys.argv[:-1]) if arg == "--mode"),
                "suite",
            )
        )
        self.launcher = WorkspaceLauncher(
            allowed_modes={"photo"} if self.mode == "photo"
            else {"video"} if self.mode == "video"
            else {"photo", "video"}
        )

    def show(self):
        if self.mode == "suite":
            self.launcher.show()
        elif self.mode in {"photo", "video"}:
            if self.mode == "photo":
                self.launcher.open_catalog()
            else:
                self.launcher.open_workspace(self.mode)
        else:
            raise ValueError(f"Unknown startup mode: {self.mode}")