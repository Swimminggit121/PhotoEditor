from PySide6.QtGui import QAction
from PySide6.QtWidgets import QToolBar
class MainToolBar(QToolBar):
    def __init__(self,window):
        super().__init__("Main Toolbar",window);self.setMovable(False)
        for text,slot in [("Open",window.open_image),("Open Project",window.open_project),("Save Project",window.save_project),("Batch Auto Edit",window.batch_auto_edit),("Photo Intelligence",window.photo_intelligence),("Auto Edit",window.auto_edit),("Auto Colour Grade",window.auto_grade),("Export",window.export_image)]:
            a=QAction(text,self);a.triggered.connect(slot);self.addAction(a)
        self.addSeparator()
        for text,slot in [("Zoom +",window.zoom_in),("Zoom -",window.zoom_out),("Fit",window.fit_image)]:
            a=QAction(text,self);a.triggered.connect(slot);self.addAction(a)
        self.addSeparator();a=QAction("Before / After",self);a.setCheckable(True);a.triggered.connect(window.toggle_before);self.addAction(a)
