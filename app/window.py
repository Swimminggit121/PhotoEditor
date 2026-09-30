from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget,QFileDialog,QLabel,QMainWindow,QMessageBox
from core.document import Document
from core.auto_grade import auto_colour_grade, auto_edit
from core.project import save_project as write_project,load_project as read_project
from image.export import export_image
from processing.batch import process_folder
from ui.adjustment_panel import AdjustmentPanel
from ui.canvas import ImageCanvas
from ui.histogram import HistogramWidget
from ui.menu_bar import MenuBar
from ui.toolbar import MainToolBar
from ui.geometry_panel import GeometryPanel
from ui.mask_panel import MaskPanel
from ui.export_dialog import ExportDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.document=Document();self.setWindowTitle("PhotoEditor");self.resize(1600,950);self.setMinimumSize(1150,700)
        self.canvas=ImageCanvas();self.setCentralWidget(self.canvas)
        self.create_menu();self.create_toolbar();self.create_adjustment_panel();self.create_geometry_panel();self.create_mask_panel();self.create_histogram();self.create_status_bar();self.update_title()
        self.canvas.crop_committed.connect(self.apply_interactive_crop)
        self.mask_panel.paint_requested.connect(self.canvas.start_brush)
        self.canvas.brush_stroke_committed.connect(self.mask_panel.add_stroke)

    def create_menu(self):self.setMenuBar(MenuBar(self))
    def create_toolbar(self):self.addToolBar(Qt.TopToolBarArea,MainToolBar(self))
    def create_adjustment_panel(self):
        self.adjustment_panel=AdjustmentPanel(self.document,self.change_adjustment)
        dock=QDockWidget("Develop",self);dock.setWidget(self.adjustment_panel);dock.setAllowedAreas(Qt.RightDockWidgetArea);dock.setMinimumWidth(390);self.addDockWidget(Qt.RightDockWidgetArea,dock)
    def create_geometry_panel(self):
        self.geometry_panel=GeometryPanel(self.document,self.change_geometry)
        self.geometry_panel.crop_requested.connect(self.canvas.start_crop)
        dock=QDockWidget("Geometry",self);dock.setWidget(self.geometry_panel);dock.setAllowedAreas(Qt.LeftDockWidgetArea);dock.setMinimumWidth(230);self.addDockWidget(Qt.LeftDockWidgetArea,dock)
    def create_mask_panel(self):
        self.mask_panel=MaskPanel(self.document,self.mask_changed)
        dock=QDockWidget("Masks",self);dock.setWidget(self.mask_panel);dock.setAllowedAreas(Qt.LeftDockWidgetArea);dock.setMinimumWidth(270);self.addDockWidget(Qt.LeftDockWidgetArea,dock)
    def create_histogram(self):
        self.histogram=HistogramWidget();dock=QDockWidget("Histogram",self);dock.setWidget(self.histogram);dock.setAllowedAreas(Qt.RightDockWidgetArea);dock.setMinimumHeight(190);self.addDockWidget(Qt.RightDockWidgetArea,dock)
    def create_status_bar(self):
        self.status_label=QLabel("Ready");self.statusBar().addPermanentWidget(self.status_label)
    def open_image(self):
        filt="Images (*.jpg *.jpeg *.png *.tif *.tiff *.webp *.bmp *.gif *.cr2 *.cr3 *.nef *.nrw *.arw *.dng *.raf *.orf *.rw2 *.pef *.srw *.3fr *.iiq *.rwl *.raw *.dcr *.kdc *.mrw *.x3f *.erf *.mef *.mos *.fff);;All Files (*)"
        path,_=QFileDialog.getOpenFileName(self,"Open Image","",filt)
        if not path:return
        try:self.document.load(path);self.refresh_view();self.status_label.setText(f"Opened: {Path(path).name}")
        except Exception as exc:QMessageBox.critical(self,"Could not open image",str(exc))
    def open_project(self):
        path,_=QFileDialog.getOpenFileName(self,"Open PhotoEditor Project","","PhotoEditor Project (*.photoedit)")
        if not path:return
        try:read_project(self.document,path);self.refresh_view();self.status_label.setText(f"Project opened: {Path(path).name}")
        except Exception as exc:QMessageBox.critical(self,"Could not open project",str(exc))
    def auto_edit(self):
        if not self.document.has_image():
            QMessageBox.information(self,"Auto Edit","Open an image first.")
            return
        try:
            self.document.adjustments=auto_edit(self.document.original_image,self.document.adjustments)
            self.document.push_history()
            self.refresh_view()
            self.status_label.setText("Auto Edit applied — full colour grade ready to refine")
        except Exception as exc:
            QMessageBox.critical(self,"Auto Edit failed",str(exc))

    def auto_grade(self):
        if not self.document.has_image():QMessageBox.information(self,"Auto Colour Grade","Open an image first.");return
        try:self.document.adjustments=auto_colour_grade(self.document.original_image,self.document.adjustments);self.document.push_history();self.refresh_view();self.status_label.setText("Auto Colour Grade applied")
        except Exception as exc:QMessageBox.critical(self,"Auto Colour Grade failed",str(exc))
    def change_adjustment(self,*args):
        if not args:return
        name,value=args[:2]
        if name=="hsl" and len(args)>=3:
            channel=args[1]; values=args[2]
            self.document.adjustments.hsl[channel]=dict(values)
        elif name.startswith("curves_") or isinstance(value,dict):
            setattr(self.document.adjustments,name,value)
        elif isinstance(value,bool):
            setattr(self.document.adjustments,name,value)
        else:
            setattr(self.document.adjustments,name,float(value))
        self.document.dirty=True;self.refresh_render()
    def change_geometry(self,name,value,commit=True):
        setattr(self.document.adjustments,name,value);self.document.dirty=True
        if commit:self.document.push_history()
        self.refresh_view()
    def apply_interactive_crop(self,left,top,right,bottom):
        a=self.document.adjustments;a.crop_left=left;a.crop_top=top;a.crop_right=right;a.crop_bottom=bottom
        self.document.push_history();self.refresh_view();self.status_label.setText("Crop applied")
    def mask_changed(self):
        self.document.dirty=True;self.refresh_render();self.mask_panel.load_selected()
    def refresh_render(self):
        if not self.document.has_image():return
        rendered=self.document.render();self.canvas.set_image(rendered,self.document.original_image);self.histogram.set_image(rendered);self.update_title()
    def refresh_view(self):
        if not self.document.has_image():return
        rendered=self.document.render();self.canvas.set_image(rendered,self.document.original_image);self.histogram.set_image(rendered);self.adjustment_panel.refresh();self.geometry_panel.refresh();self.update_title()
        self.mask_panel.list.clear()
        for m in self.document.adjustments.local_adjustments:self.mask_panel.list.addItem(m.get("name","Mask"))
        if self.document.adjustments.local_adjustments:self.mask_panel.list.setCurrentRow(0)
    def undo(self):
        if self.document.undo():self.refresh_view()
    def redo(self):
        if self.document.redo():self.refresh_view()
    def reset_adjustments(self):
        if self.document.has_image():self.document.reset_adjustments();self.refresh_view()
    def zoom_in(self):self.canvas.zoom_in()
    def zoom_out(self):self.canvas.zoom_out()
    def fit_image(self):self.canvas.reset_view()
    def toggle_before(self):self.canvas.toggle_before()
    def batch_export(self):
        input_dir=QFileDialog.getExistingDirectory(self,"Choose Input Folder")
        if not input_dir:return
        output_dir=QFileDialog.getExistingDirectory(self,"Choose Output Folder")
        if not output_dir:return
        try:
            results=process_folder(input_dir,output_dir,auto_grade=False,quality=95)
            self.status_label.setText(f"Batch export complete: {len(results)} images")
            QMessageBox.information(self,"Batch Export",f"Exported {len(results)} images.")
        except Exception as exc:
            QMessageBox.critical(self,"Batch Export failed",str(exc))

    def export_image(self):
        if not self.document.has_image():QMessageBox.information(self,"Export","Open an image first.");return
        dlg=ExportDialog(self)
        if dlg.exec()!=dlg.Accepted:return
        ext=dlg.extension();default=str((self.document.path.parent if self.document.path else Path.home())/(Path(self.document.path.stem if self.document.path else "edited").stem+"_edited"+ext))
        path,_=QFileDialog.getSaveFileName(self,"Export Image",default,f"{dlg.format.currentText()} (*{ext})")
        if not path:return
        if Path(path).suffix.lower()!=ext:path+=ext
        try:export_image(self.document.render(),path,dlg.quality_value());self.status_label.setText(f"Exported: {Path(path).name}")
        except Exception as exc:QMessageBox.critical(self,"Export failed",str(exc))
    def save_project(self):
        if not self.document.has_image():QMessageBox.information(self,"Save Project","Open an image first.");return
        default=str((self.document.path.parent if self.document.path else Path.home())/(self.document.path.stem if self.document.path else "project"))+".photoedit"
        path,_=QFileDialog.getSaveFileName(self,"Save PhotoEditor Project",default,"PhotoEditor Project (*.photoedit)")
        if not path:return
        if not path.lower().endswith(".photoedit"):path+=".photoedit"
        try:write_project(self.document,path);self.update_title();self.status_label.setText(f"Saved: {Path(path).name}")
        except Exception as exc:QMessageBox.critical(self,"Save failed",str(exc))
    def update_title(self):
        marker=" *" if self.document.dirty else "";self.setWindowTitle(f"PhotoEditor — {self.document.path.name}{marker}" if self.document.path else "PhotoEditor")
    def closeEvent(self,event):
        if self.document.dirty:
            result=QMessageBox.question(self,"Unsaved Changes","You have unsaved changes. Are you sure you want to exit?",QMessageBox.Yes|QMessageBox.No)
            if result!=QMessageBox.Yes:event.ignore();return
        event.accept()
