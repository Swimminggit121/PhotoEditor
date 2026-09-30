from PySide6.QtWidgets import QWidget,QVBoxLayout,QPushButton,QLabel,QSlider
from PySide6.QtCore import Qt
class GeometryPanel(QWidget):
    def __init__(self,document,on_change,parent=None):
        super().__init__(parent);self.document=document;self.on_change=on_change;layout=QVBoxLayout(self);layout.addWidget(QLabel("Transform"))
        for text,fn in [("Rotate 90° Left",lambda:self.change("rotation",self.document.adjustments.rotation-90)),("Rotate 90° Right",lambda:self.change("rotation",self.document.adjustments.rotation+90)),("Flip Horizontal",lambda:self.toggle("flip_horizontal")),("Flip Vertical",lambda:self.toggle("flip_vertical"))]:
            b=QPushButton(text);b.clicked.connect(fn);layout.addWidget(b)
        layout.addWidget(QLabel("Straighten / Rotate"));self.rotation=QSlider(Qt.Horizontal);self.rotation.setRange(-180,180);self.rotation.valueChanged.connect(lambda v:self.change("rotation",v));layout.addWidget(self.rotation)
        layout.addWidget(QLabel("Crop"))
        for text,ratio in [("Original","original"),("Square 1:1","1:1"),("Landscape 4:3","4:3"),("Landscape 16:9","16:9"),("Portrait 3:4","3:4")]:
            b=QPushButton(text);b.clicked.connect(lambda _,r=ratio:self.crop(r));layout.addWidget(b)
        b=QPushButton("Reset Geometry");b.clicked.connect(self.reset);layout.addWidget(b);layout.addStretch()
    def change(self,key,value):self.on_change(key,value,True)
    def toggle(self,key):self.on_change(key,not getattr(self.document.adjustments,key),True)
    def crop(self,ratio):
        if ratio=="original":vals=(0.,0.,1.,1.)
        else:
            rw,rh=map(float,ratio.split(":")); target=rw/rh
            w,h=self.document.original_image.size; current=w/h
            if current>target:
                nw=target/current; margin=(1-nw)/2; vals=(margin,0,1-margin,1)
            else:
                nh=current/target; margin=(1-nh)/2; vals=(0,margin,1,1-margin)
        for k,v in zip(("crop_left","crop_top","crop_right","crop_bottom"),vals):self.on_change(k,v,True)
    def reset(self):
        for k,v in [("rotation",0),("flip_horizontal",False),("flip_vertical",False),("crop_left",0.),("crop_top",0.),("crop_right",1.),("crop_bottom",1.)]:self.on_change(k,v,True)
    def refresh(self):
        self.rotation.blockSignals(True);self.rotation.setValue(int(self.document.adjustments.rotation));self.rotation.blockSignals(False)
