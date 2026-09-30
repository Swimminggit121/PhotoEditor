from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar

class MenuBar(QMenuBar):
    def __init__(self,window):
        super().__init__(window)
        file_menu=self.addMenu("File")
        def action(text,shortcut,slot):
            a=QAction(text,self)
            if shortcut:a.setShortcut(shortcut)
            a.triggered.connect(slot); return a
        file_menu.addAction(action("Open...","Ctrl+O",window.open_image))
        file_menu.addAction(action("Export...","Ctrl+Shift+S",window.export_image))
        file_menu.addSeparator()
        file_menu.addAction(action("Save Project","Ctrl+S",window.save_project))
        file_menu.addSeparator()
        file_menu.addAction(action("Exit","Ctrl+Q",window.close))

        edit_menu=self.addMenu("Edit")
        edit_menu.addAction(action("Undo","Ctrl+Z",window.undo))
        edit_menu.addAction(action("Redo","Ctrl+Y",window.redo))
        edit_menu.addSeparator()
        edit_menu.addAction(action("Auto Colour Grade","Ctrl+G",window.auto_grade))
        edit_menu.addAction(action("Reset Adjustments","",window.reset_adjustments))

        view_menu=self.addMenu("View")
        view_menu.addAction(action("Zoom In","+",window.zoom_in))
        view_menu.addAction(action("Zoom Out","-",window.zoom_out))
        view_menu.addAction(action("Fit Image","F",window.fit_image))
        view_menu.addAction(action("Before / After","B",window.toggle_before))
