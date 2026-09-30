from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGroupBox,QHBoxLayout,QLabel,QListWidget,QPushButton,QSlider,QVBoxLayout

class MaskPanel(QGroupBox):
    paint_requested=Signal()
    def __init__(self,document,on_change,parent=None):
        super().__init__("Masks / Local Adjustments",parent)
        self.document=document;self.on_change=on_change
        layout=QVBoxLayout(self);self.list=QListWidget();layout.addWidget(self.list)
        row=QHBoxLayout()
        for label,kind in [("Brush","brush"),("Linear","linear"),("Radial","radial")]:
            b=QPushButton(label);b.clicked.connect(lambda _,k=kind:self.add_mask(k));row.addWidget(b)
        layout.addLayout(row)
        self.paint=QPushButton("Paint Selected Brush");self.paint.clicked.connect(self.paint_selected);layout.addWidget(self.paint)
        self.invert=QPushButton("Invert Selected");self.invert.clicked.connect(self.toggle_invert);layout.addWidget(self.invert)
        self.feather=QSlider(Qt.Horizontal);self.feather.setRange(0,100);self.feather.setValue(0);layout.addWidget(QLabel("Feather"));layout.addWidget(self.feather)
        self.density=QSlider(Qt.Horizontal);self.density.setRange(0,100);self.density.setValue(100);layout.addWidget(QLabel("Density"));layout.addWidget(self.density)
        for title,key in [("Local Exposure","exposure"),("Local Contrast","contrast"),("Local Temperature","temperature"),("Local Saturation","saturation")]:
            setattr(self,key,QSlider(Qt.Horizontal));w=getattr(self,key);w.setRange(-100,100);layout.addWidget(QLabel(title));layout.addWidget(w)
            w.valueChanged.connect(lambda v,k=key:self.update_local(k,v))
        self.feather.valueChanged.connect(lambda v:self.update_selected("feather",v))
        self.density.valueChanged.connect(lambda v:self.update_selected("density",v/100))
        self.list.currentRowChanged.connect(self.load_selected)

    def add_mask(self,kind):
        from masks.manager import MaskManager
        masks=self.document.adjustments.local_adjustments
        masks.append({"brush":MaskManager.new_brush,"linear":MaskManager.new_linear,"radial":MaskManager.new_radial}[kind]())
        self.list.addItem(masks[-1]["name"]);self.list.setCurrentRow(len(masks)-1);self.document.dirty=True;self.on_change()

    def selected(self):
        i=self.list.currentRow();masks=self.document.adjustments.local_adjustments
        return masks[i] if 0<=i<len(masks) else None

    def paint_selected(self):
        m=self.selected()
        if m and m.get("type")=="brush":self.paint_requested.emit()

    def add_stroke(self,points):
        m=self.selected()
        if not m or m.get("type")!="brush":return
        m.setdefault("strokes",[]).append({"points":points,"radius":35.0});self.document.dirty=True;self.on_change()

    def load_selected(self):
        m=self.selected()
        if not m:return
        self.invert.setText("Uninvert Selected" if m.get("invert") else "Invert Selected")
        self._set(self.feather,int(m.get("feather",0)));self._set(self.density,int(m.get("density",1)*100))
        local=m.get("local",{})
        for key in ("exposure","contrast","temperature","saturation"):self._set(getattr(self,key),int(local.get(key,0)))

    def _set(self,w,v):
        w.blockSignals(True);w.setValue(v);w.blockSignals(False)

    def update_selected(self,key,value):
        m=self.selected()
        if m:m[key]=value;self.document.dirty=True;self.on_change()

    def update_local(self,key,value):
        m=self.selected()
        if m:m.setdefault("local",{})[key]=float(value);self.document.dirty=True;self.on_change()

    def toggle_invert(self):
        m=self.selected()
        if m:m["invert"]=not m.get("invert",False);self.load_selected();self.document.dirty=True;self.on_change()
