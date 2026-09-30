from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolBar

class MainToolBar(QToolBar):
    def __init__(self,window):
        super().__init__("Main Toolbar",window)
        self.setMovable(False)
        for text,slot in [("Open",window.open_image),("Auto Colour Grade",window.auto_grade)]:
            a=QAction(text,self); a.triggered.connect(slot); self.addAction(a)
        self.addSeparator()
        for text,slot in [("Zoom +",window.zoom_in),("Zoom -",window.zoom_out),("Fit",window.fit_image)]:
            a=QAction(text,self); a.triggered.connect(slot); self.addAction(a)
        self.addSeparator()
        before=QAction("Before / After",self); before.setCheckable(True); before.triggered.connect(window.toggle_before); self.addAction(before)
