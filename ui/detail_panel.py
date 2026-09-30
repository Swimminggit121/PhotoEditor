from PySide6.QtWidgets import QWidget,QVBoxLayout
from ui.sliders import AdjustmentSlider
class DetailPanel(QWidget):
    def __init__(self,document,on_change,parent=None):
        super().__init__(parent);self.document=document;self.on_change=on_change;layout=QVBoxLayout(self);self.sliders={}
        for label,key,lo,hi in [("Texture","texture",-100,100),("Clarity","clarity",-100,100),("Dehaze","dehaze",-100,100),("Sharpening","sharpening",0,100),("Noise Reduction","noise_reduction",0,100),("Grain","grain",0,100),("Vignette","vignette",-100,100),("Lens Correction","lens_correction",-100,100),("Chromatic Aberration","chromatic_aberration",-100,100),("Distortion","distortion",-100,100)]:
            s=AdjustmentSlider(label,lo,hi,0);s.valueChanged.connect(lambda v,k=key:self.on_change(k,v));self.sliders[key]=s;layout.addWidget(s)
        layout.addStretch()
    def refresh(self):
        for k,s in self.sliders.items():s.blockSignals(True);s.setValue(getattr(self.document.adjustments,k));s.blockSignals(False)
