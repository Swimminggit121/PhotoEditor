from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar
class MenuBar(QMenuBar):
    def __init__(self,window):
        super().__init__(window)
        def action(menu,text,shortcut,slot):
            a=QAction(text,self)
            if shortcut:a.setShortcut(shortcut)
            a.triggered.connect(slot);menu.addAction(a)
        f=self.addMenu("File");action(f,"Open...","Ctrl+O",window.open_image);action(f,"Open Project...","Ctrl+Shift+O",window.open_project);action(f,"Export...","Ctrl+Shift+S",window.export_image);action(f,"Save Project","Ctrl+S",window.save_project);f.addSeparator();action(f,"Exit","Ctrl+Q",window.close)
        e=self.addMenu("Edit");action(e,"Undo","Ctrl+Z",window.undo);action(e,"Redo","Ctrl+Y",window.redo);e.addSeparator();action(e,"Auto Colour Grade","Ctrl+G",window.auto_grade);action(e,"Reset Adjustments","",window.reset_adjustments)
        v=self.addMenu("View");action(v,"Zoom In","+ ",window.zoom_in);action(v,"Zoom Out","-",window.zoom_out);action(v,"Fit Image","F",window.fit_image);action(v,"Before / After","B",window.toggle_before)
