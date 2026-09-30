from PySide6.QtWidgets import QWidget,QVBoxLayout,QPushButton,QLabel,QSlider
from PySide6.QtCore import Qt
class GeometryPanel(QWidget):
    def __init__(self,document,on_change,parent=None):
        super().__init__(parent);self.document=document;self.on_change=on_change;layout=QVBoxLayout(self);layout.addWidget(QLabel("Transform"))
        for text,fn in [("Rotate 90° Left",lambda:self.change("rotation",self.document.adjustments.rotation-90)),("Rotate 90° Right",lambda:self.change("rotation",self.document.adjustments.rotation+90)),("Flip Horizontal",lambda:self.toggle("flip_horizontal")),("Flip Vertical",lambda:self.toggle("flip_vertical")),("Reset Geometry",self.reset)]:
            b=QPushButton(text);b.clicked.connect(fn);layout.addWidget(b)
        layout.addWidget(QLabel("Straighten / Rotate"));self.rotation=QSlider(Qt.Horizontal);self.rotation.setRange(-180,180);self.rotation.valueChanged.connect(lambda v:self.change("rotation",v));layout.addWidget(self.rotation);layout.addStretch()
    def change(self,key,value):self.on_change(key,value,True)
    def toggle(self,key):self.on_change(key,not getattr(self.document.adjustments,key),True)
    def reset(self):self.on_change("rotation",0,True);self.on_change("flip_horizontal",False,True);self.on_change("flip_vertical",False,True)
    def refresh(self):self.rotation.blockSignals(True);self.rotation.setValue(int(self.document.adjustments.rotation));self.rotation.blockSignals(False)
