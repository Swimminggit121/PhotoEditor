from PySide6.QtWidgets import QDialog,QFormLayout,QComboBox,QSlider,QDialogButtonBox,QLabel
from PySide6.QtCore import Qt
class ExportDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle("Export Settings");form=QFormLayout(self)
        self.format=QComboBox();self.format.addItems(["JPEG","PNG","TIFF","WebP"])
        self.quality=QSlider(Qt.Horizontal);self.quality.setRange(1,100);self.quality.setValue(95);self.quality_label=QLabel("95");self.quality.valueChanged.connect(lambda v:self.quality_label.setText(str(v)))
        form.addRow("Format",self.format);form.addRow("Quality",self.quality);form.addRow("",self.quality_label)
        b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);b.accepted.connect(self.accept);b.rejected.connect(self.reject);form.addRow(b)
    def extension(self):return {"JPEG":".jpg","PNG":".png","TIFF":".tif","WebP":".webp"}[self.format.currentText()]
    def quality_value(self):return self.quality.value()
