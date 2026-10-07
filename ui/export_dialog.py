from dataclasses import replace

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSlider,
)
from PySide6.QtCore import Qt

from image.export import EXPORT_RECIPES


class ExportDialog(QDialog):
    def __init__(self,parent=None,batch_mode=False):
        super().__init__(parent);self.setWindowTitle("Export Settings");form=QFormLayout(self)
        self.recipe=QComboBox()
        for recipe in EXPORT_RECIPES:
            self.recipe.addItem(recipe.label, recipe)
        self.recipe.setCurrentIndex(0)
        self.format=QComboBox();self.format.addItems(["JPEG","PNG","TIFF","WebP"])
        self.recipe.currentIndexChanged.connect(self._recipe_changed)
        self.recipe.currentIndexChanged.connect(self._sync_format)
        self.quality=QSlider(Qt.Horizontal);self.quality.setRange(1,100);self.quality.setValue(95);self.quality_label=QLabel("95");self.quality.valueChanged.connect(lambda v:self.quality_label.setText(str(v)))
        self.max_dimension=QLineEdit("2048")
        self.max_dimension.setPlaceholderText("0 = keep original pixel dimensions")
        self.include_metadata=QCheckBox("Include source metadata, including any recorded location")
        self.embed_srgb=QCheckBox("Embed an sRGB output profile")
        self.embed_srgb.setChecked(True)
        self.master_hint=QLabel("16-bit TIFF retains supported RAW/16-bit source precision; 8-bit sources do not gain detail.")
        self.master_hint.setWordWrap(True)
        self.master_hint.setVisible(False)
        self.auto_edit=QCheckBox("Apply optional per-photo automatic editing (on this device)")
        self.auto_edit.setVisible(batch_mode)
        form.addRow("Export recipe",self.recipe)
        form.addRow("Format",self.format)
        form.addRow("Maximum long edge (px)",self.max_dimension)
        form.addRow("Quality",self.quality);form.addRow("",self.quality_label)
        form.addRow("",self.include_metadata)
        form.addRow("",self.embed_srgb)
        form.addRow("",self.master_hint)
        if batch_mode:
            form.addRow("",self.auto_edit)
        b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);b.accepted.connect(self.accept);b.rejected.connect(self.reject);form.addRow(b)
        self._recipe_changed(0)
    def _sync_format(self):
        is_master = self.recipe.currentData().bit_depth == 16
        self.format.setCurrentText({
            ".jpg": "JPEG", ".png": "PNG", ".tif": "TIFF", ".webp": "WebP"
        }[self.recipe.currentData().extension])
        self.format.setEnabled(not is_master)
    def _recipe_changed(self,index):
        recipe=self.recipe.itemData(index)
        if recipe is None:return
        self.quality.setValue(recipe.quality)
        self.max_dimension.setText(str(recipe.max_dimension or 0))
        is_master = recipe.bit_depth == 16
        self.include_metadata.setEnabled(not is_master)
        if is_master:
            self.include_metadata.setChecked(False)
        self.master_hint.setVisible(is_master)
    def current_recipe(self):
        recipe=self.recipe.currentData()
        try:
            dimension=int(self.max_dimension.text() or "0")
        except ValueError as exc:
            raise ValueError("Maximum image dimension must be a whole number; use 0 for full size.") from exc
        if dimension < 0:
            raise ValueError("Maximum image dimension cannot be negative.")
        return replace(
            recipe,
            extension=recipe.extension if recipe.bit_depth == 16 else self.extension(),
            quality=self.quality_value(),
            max_dimension=dimension or None,
            include_metadata=self.include_metadata.isChecked() if recipe.bit_depth == 8 else False,
            embed_srgb=self.embed_srgb.isChecked(),
        )
    def extension(self):return {"JPEG":".jpg","PNG":".png","TIFF":".tif","WebP":".webp"}[self.format.currentText()]
    def quality_value(self):return self.quality.value()
