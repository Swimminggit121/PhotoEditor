from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QThreadPool
from PySide6.QtWidgets import QApplication,QDockWidget,QFileDialog,QInputDialog,QLabel,QMainWindow,QMessageBox,QScrollArea
from core.document import Document
from core.auto_grade import auto_colour_grade, auto_edit
from core.project import save_project as write_project,load_project as read_project
from image.export import export_image, srgb_profile_bytes
from image.loader import is_raw
from presets.manager import save_preset
from ui.adjustment_panel import AdjustmentPanel
from ui.canvas import ImageCanvas
from ui.histogram import HistogramWidget
from ui.menu_bar import MenuBar
from ui.toolbar import MainToolBar
from ui.geometry_panel import GeometryPanel
from ui.mask_panel import MaskPanel
from ui.export_dialog import ExportDialog
from ui.batch_editor_dialog import BatchEditorDialog
from ui.preset_manager import PresetManagerDialog
from ui.video_montage_dialog import VideoMontageDialog
from ui.help_dialog import HelpDialog
from ui.preview_worker import PreviewTask
from ui.photo_catalog_window import PhotoCatalogWindow

class MainWindow(QMainWindow):
    def __init__(self,on_home=None,suite_mode=False,on_catalog=None):
        super().__init__();self.document=Document();self.setWindowTitle("PhotoEditor")
        self.on_home=on_home
        self.suite_mode=suite_mode
        self.on_catalog=on_catalog
        self.catalog_window=None
        self._full_resolution_view=False
        screen=QApplication.primaryScreen();available=screen.availableGeometry() if screen else None
        self.setMinimumSize(850,560)
        self.resize(min(1600,available.width()-60) if available else 1400,min(950,available.height()-80) if available else 850)
        self.canvas=ImageCanvas();self.setCentralWidget(self.canvas);self._render_timer=QTimer(self);self._render_timer.setSingleShot(True);self._render_timer.timeout.connect(self._perform_preview_render)
        self._history_timer=QTimer(self);self._history_timer.setSingleShot(True);self._history_timer.setInterval(250);self._history_timer.timeout.connect(self._commit_adjustment_history)
        self._preview_pool=QThreadPool(self);self._preview_pool.setMaxThreadCount(1);self._preview_generation=0;self._preview_running=False;self._preview_pending=None;self._preview_source_original=None;self._preview_source_image=None
        self.create_menu();self.create_toolbar();self.create_adjustment_panel();self.create_geometry_panel();self.create_mask_panel();self.create_histogram();self.create_status_bar();self.update_title()
        self.canvas.crop_committed.connect(self.apply_interactive_crop)
        self.mask_panel.paint_requested.connect(self.canvas.start_brush)
        self.canvas.brush_stroke_committed.connect(self.mask_panel.add_stroke)

    def create_menu(self):self.setMenuBar(MenuBar(self))
    def create_toolbar(self):self.addToolBar(Qt.TopToolBarArea,MainToolBar(self))
    def create_adjustment_panel(self):
        self.adjustment_panel=AdjustmentPanel(self.document,self.change_adjustment)
        dock=QDockWidget("Develop",self);dock.setWidget(self.adjustment_panel);dock.setAllowedAreas(Qt.RightDockWidgetArea);dock.setMinimumWidth(320);self.addDockWidget(Qt.RightDockWidgetArea,dock)
    def create_geometry_panel(self):
        self.geometry_panel=GeometryPanel(self.document,self.change_geometry)
        self.geometry_panel.crop_requested.connect(self.canvas.start_crop)
        content=QScrollArea();content.setWidgetResizable(True);content.setWidget(self.geometry_panel)
        dock=QDockWidget("Geometry",self);dock.setWidget(content);dock.setAllowedAreas(Qt.LeftDockWidgetArea);dock.setMinimumWidth(190);self.addDockWidget(Qt.LeftDockWidgetArea,dock)
    def create_mask_panel(self):
        self.mask_panel=MaskPanel(self.document,self.mask_changed)
        content=QScrollArea();content.setWidgetResizable(True);content.setWidget(self.mask_panel)
        dock=QDockWidget("Masks",self);dock.setWidget(content);dock.setAllowedAreas(Qt.LeftDockWidgetArea);dock.setMinimumWidth(210);self.addDockWidget(Qt.LeftDockWidgetArea,dock)
    def create_histogram(self):
        self.histogram=HistogramWidget();dock=QDockWidget("Histogram",self);dock.setWidget(self.histogram);dock.setAllowedAreas(Qt.RightDockWidgetArea);dock.setMinimumHeight(190);self.addDockWidget(Qt.RightDockWidgetArea,dock)
    def create_status_bar(self):
        self.status_label=QLabel("Ready");self.statusBar().addPermanentWidget(self.status_label)
    def open_image(self):
        filt="Images (*.jpg *.jpeg *.png *.tif *.tiff *.webp *.bmp *.gif *.cr2 *.cr3 *.nef *.nrw *.arw *.dng *.raf *.orf *.rw2 *.pef *.srw *.3fr *.iiq *.rwl *.raw *.dcr *.kdc *.mrw *.x3f *.erf *.mef *.mos *.fff);;All Files (*)"
        path,_=QFileDialog.getOpenFileName(self,"Open Image","",filt)
        if not path:return
        self.open_image_path(path)

    def open_image_path(self,path):
        if not self._confirm_replace_document():return
        try:
            self.document.load(path);self._full_resolution_view=False;self.refresh_view()
            self.status_label.setText(
                f"Opened: {Path(path).name}" + (
                    f" · {self.document.precision_warning}"
                    if self.document.precision_warning else ""
                )
            )
            return True
        except Exception as exc:QMessageBox.critical(self,"Could not open image",str(exc))
        return False
    def open_project(self):
        path,_=QFileDialog.getOpenFileName(self,"Open PhotoEditor Project","","PhotoEditor Project (*.photoedit)")
        if not path:return
        if not self._confirm_replace_document():return
        try:read_project(self.document,path);self.refresh_view();self.status_label.setText(f"Project opened: {Path(path).name}")
        except Exception as exc:QMessageBox.critical(self,"Could not open project",str(exc))

    def _confirm_replace_document(self):
        if not self.document.dirty:return True
        answer=QMessageBox.warning(
            self,"Unsaved Changes","Save your photo edits before opening another file?",
            QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Save,
        )
        if answer==QMessageBox.Save:return self.save_project()
        return answer==QMessageBox.Discard

    def _commit_adjustment_history(self):
        current=self.document.history.current
        if current is not None and current!=self.document.adjustments:
            self.document.push_history()

    def auto_edit(self):
        if not self.document.has_image():
            QMessageBox.information(self,"Auto Edit","Open an image first.")
            return
        try:
            file_kind = (
                "raw" if self.document.path and is_raw(self.document.path)
                else (
                    "jpeg"
                    if self.document.path and self.document.path.suffix.lower() in {".jpg", ".jpeg"}
                    else self.document.path.suffix.lower().lstrip(".")
                    if self.document.path else "generic"
                )
            )
            self.document.adjustments=auto_edit(
                self.document.analysis_image,self.document.adjustments,file_kind
            )
            self.document.push_history()
            self.refresh_view()
            self.status_label.setText("Auto Edit applied — full colour grade ready to refine")
        except Exception as exc:
            QMessageBox.critical(self,"Auto Edit failed",str(exc))

    def auto_grade(self):
        if not self.document.has_image():QMessageBox.information(self,"Auto Colour Grade","Open an image first.");return
        try:self.document.adjustments=auto_colour_grade(self.document.analysis_image,self.document.adjustments);self.document.push_history();self.refresh_view();self.status_label.setText("Auto Colour Grade applied")
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
        self.document.dirty=True;self._history_timer.start();self._render_timer.start(35)
    def change_geometry(self,name,value,commit=True):
        setattr(self.document.adjustments,name,value);self.document.dirty=True
        if commit:
            self.document.push_history()
            self.refresh_view()
        else:
            self._render_timer.start(45)
    def apply_interactive_crop(self,left,top,right,bottom):
        a=self.document.adjustments;a.crop_left=left;a.crop_top=top;a.crop_right=right;a.crop_bottom=bottom
        self.document.push_history();self.refresh_view();self.status_label.setText("Crop applied")
    def mask_changed(self):
        self.document.dirty=True;self.mask_panel.load_selected();self._render_timer.start(45)
    def _perform_preview_render(self,full_resolution=None):
        if not self.document.has_image():return
        if full_resolution is None:
            full_resolution=self._full_resolution_view
        self._preview_generation+=1
        source=self.document.original_image
        cached_source=None if full_resolution else (self._preview_source_image if self._preview_source_original is source else None)
        self._preview_pending=(
            self._preview_generation,
            source,
            self.document.adjustments.copy(),
            None if full_resolution else self.document.preview_max_size,
            cached_source,
        )
        self._start_pending_preview()

    def _start_pending_preview(self):
        if self._preview_running or self._preview_pending is None:return
        generation,source,adjustments,max_size,cached_source=self._preview_pending
        self._preview_pending=None
        self._preview_running=True
        precision_source = self.document.native_pixels
        task=PreviewTask(generation,source,adjustments,max_size,cached_source,precision_source)
        task.signals.ready.connect(self._preview_ready)
        task.signals.failed.connect(self._preview_failed)
        self._preview_pool.start(task)

    def _preview_ready(self,generation,source,preview_source,rendered,full_resolution):
        self._preview_running=False
        if source is self.document.original_image:
            self._preview_source_original=source
            self._preview_source_image=preview_source
            self.document._preview_source=preview_source
            if generation==self._preview_generation:
                self.canvas.set_image(rendered,preview_source)
                self.histogram.set_image(rendered)
                self.update_title()
                self._full_resolution_view = full_resolution
                if self._full_resolution_view:
                    self.canvas.zoom=1.0
                    self.canvas.offset=self.canvas.rect().center()
                    self.canvas.update()
                self.status_label.setText(
                    (
                        f"100% source pixels · {rendered.width}×{rendered.height}"
                        if self._full_resolution_view else "Edited preview"
                    ) + (
                        f" · {self.document.precision_warning}"
                        if self.document.precision_warning else ""
                    )
                )
        self._start_pending_preview()

    def _preview_failed(self,generation,message):
        self._preview_running=False
        if generation==self._preview_generation:
            self.status_label.setText(f"Preview failed: {message}")
        self._start_pending_preview()

    def refresh_render(self):
        self._render_timer.stop()
        self._perform_preview_render()
    def refresh_view(self):
        if not self.document.has_image():return
        self._render_timer.stop();self.adjustment_panel.refresh();self.geometry_panel.refresh();self.update_title()
        self.mask_panel.list.clear()
        for m in self.document.adjustments.local_adjustments:self.mask_panel.list.addItem(m.get("name","Mask"))
        if self.document.adjustments.local_adjustments:self.mask_panel.list.setCurrentRow(0)
        self._perform_preview_render()
    def undo(self):
        self._history_timer.stop();self._commit_adjustment_history()
        if self.document.undo():self.refresh_view()
    def redo(self):
        self._history_timer.stop();self._commit_adjustment_history()
        if self.document.redo():self.refresh_view()
    def reset_adjustments(self):
        if self.document.has_image():self.document.reset_adjustments();self.refresh_view()
    def zoom_in(self):self.canvas.zoom_in()
    def zoom_out(self):self.canvas.zoom_out()
    def fit_image(self):
        self._full_resolution_view=False
        if self.document.has_image():
            self.canvas.set_image(None)
            self._perform_preview_render()
        self.canvas.reset_view()
    def show_workspace_hub(self):
        if self.on_home:self.on_home()
    def open_catalog(self):
        if self.on_catalog:
            self.on_catalog()
            return
        if self.catalog_window is None:
            self.catalog_window=PhotoCatalogWindow(self)
            self.catalog_window.photo_selected.connect(self.open_image_path)
            self.catalog_window.photo_workspace_requested.connect(self._show_photo_editor)
            self.catalog_window.video_requested.connect(
                lambda paths:self.create_video_montage(initial_paths=paths)
            )
        self.catalog_window.show();self.catalog_window.raise_();self.catalog_window.activateWindow()
    def _show_photo_editor(self):
        if self.catalog_window:self.catalog_window.hide()
        self.show();self.raise_();self.activateWindow()
    def view_full_resolution(self):
        if not self.document.has_image():
            QMessageBox.information(self,"100% Detail","Open an image first.")
            return
        self._full_resolution_view=True
        self.canvas.set_image(None)
        self.status_label.setText("Rendering a full-resolution inspection view…")
        self._render_timer.stop()
        self._perform_preview_render(full_resolution=True)
    def toggle_before(self):self.canvas.toggle_before()
    def batch_auto_edit(self):
        dlg=BatchEditorDialog(self)
        dlg.exec()

    def save_current_preset(self):
        if not self.document.has_image():
            QMessageBox.information(self,"Save Preset","Open an image first.")
            return
        name,ok=QInputDialog.getText(self,"Save Preset","Preset name:",text="custom-look")
        if not ok or not name.strip():
            return
        try:
            path=save_preset(self.document.adjustments,name.strip())
            self.status_label.setText(f"Preset saved: {path.name}")
        except Exception as exc:
            QMessageBox.critical(self,"Save Preset",str(exc))

    def manage_presets(self):
        dlg=PresetManagerDialog(self)
        dlg.exec()

    def create_video_montage(self,checked=False,initial_paths=None):
        dlg=VideoMontageDialog(self,suite_mode=self.suite_mode,initial_paths=initial_paths)
        dlg.exec()

    def show_help(self):
        dlg=HelpDialog(self)
        dlg.exec()

    def export_image(self):
        if not self.document.has_image():QMessageBox.information(self,"Export","Open an image first.");return
        dlg=ExportDialog(self)
        if dlg.exec()!=dlg.Accepted:return
        try:recipe=dlg.current_recipe()
        except ValueError as exc:QMessageBox.warning(self,"Check export settings",str(exc));return
        ext=recipe.extension
        if self.document.path:
            source=self.document.path.resolve()
            originals=source.parent
            export_folder=originals.parent/f"{originals.name}_Edited"
            default=str(export_folder/(source.stem+"_edited"+ext))
        else:default=str(Path.home()/"PhotoEditor_Edited"/("edited"+ext))
        path,_=QFileDialog.getSaveFileName(self,"Export Image",default,f"{dlg.format.currentText()} (*{ext})")
        if not path:return
        if Path(path).suffix.lower()!=ext:path+=ext
        try:
            destination=Path(path).expanduser().resolve()
            if self.document.path:
                source=self.document.path.resolve()
                if destination==source:
                    raise ValueError("An export cannot overwrite the original photo.")
                if source.parent==destination.parent or source.parent in destination.parents:
                    raise ValueError("Choose a folder outside the originals folder so originals and edited copies stay separate.")
            from core.photo_catalog import export_metadata
            metadata=export_metadata(self.document.path) if recipe.include_metadata and self.document.path else None
            export_image(
                self.document.render_master(),
                destination,
                recipe.quality,
                metadata=metadata,
                icc_profile=srgb_profile_bytes() if recipe.embed_srgb else None,
                max_dimension=recipe.max_dimension,
            )
            self.status_label.setText(f"Exported: {destination.name}")
        except Exception as exc:QMessageBox.critical(self,"Export failed",str(exc))
    def save_project(self):
        if not self.document.has_image():QMessageBox.information(self,"Save Project","Open an image first.");return False
        default=str((self.document.path.parent if self.document.path else Path.home())/(self.document.path.stem if self.document.path else "project"))+".photoedit"
        path,_=QFileDialog.getSaveFileName(self,"Save PhotoEditor Project",default,"PhotoEditor Project (*.photoedit)")
        if not path:return False
        if not path.lower().endswith(".photoedit"):path+=".photoedit"
        self._history_timer.stop();self._commit_adjustment_history()
        try:write_project(self.document,path);self.update_title();self.status_label.setText(f"Saved: {Path(path).name}");return True
        except Exception as exc:QMessageBox.critical(self,"Save failed",str(exc));return False
    def update_title(self):
        marker=" *" if self.document.dirty else "";self.setWindowTitle(f"PhotoEditor — {self.document.path.name}{marker}" if self.document.path else "PhotoEditor")
    def closeEvent(self,event):
        if self.document.dirty:
            result=QMessageBox.warning(self,"Unsaved Changes","Save your photo edits before closing?",QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Save)
            if result==QMessageBox.Save:
                if not self.save_project():event.ignore();return
            elif result!=QMessageBox.Discard:
                event.ignore();return
        event.accept()
