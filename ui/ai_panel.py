from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QObject, Slot
from PySide6.QtWidgets import QGroupBox,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QProgressBar,QFileDialog,QComboBox,QMessageBox
from ai.analysis import analyze_image
from ai.masks import sky_mask, subject_mask, mask_to_local_adjustment
from ai.model_manager import ModelManager
from ai.runtime import runtime_info
from ai.smart_crop import smart_crop
from ai.style import reference_grade, reference_similarity

class AIWorker(QObject):
    finished=Signal(object); error=Signal(str)
    def __init__(self,image): super().__init__(); self.image=image
    @Slot()
    def run(self):
        try:self.finished.emit(analyze_image(self.image,True))
        except Exception as e:self.error.emit(str(e))

class AIPanel(QGroupBox):
    analysis_ready=Signal(object)
    mask_ready=Signal(object)
    grade_ready=Signal(object)
    crop_ready=Signal(object)
    enhance_requested=Signal(float,int)
    def __init__(self,window,parent=None):
        super().__init__("AI Studio",parent); self.window=window; self.thread=None; self.worker=None
        lay=QVBoxLayout(self)
        self.status=QLabel("AI ready"); self.status.setWordWrap(True); lay.addWidget(self.status)
        self.backend=QLabel(""); self.backend.setWordWrap(True); lay.addWidget(self.backend)
        self.progress=QProgressBar();self.progress.setRange(0,0);self.progress.hide();lay.addWidget(self.progress)
        b=QPushButton("Analyse Current Photo");b.clicked.connect(self.analyse);lay.addWidget(b)
        row=QHBoxLayout()
        for text,slot in [("Subject Mask",self.subject),("Sky Mask",self.sky),("Smart Crop",self.crop)]:
            x=QPushButton(text);x.clicked.connect(slot);row.addWidget(x)
        lay.addLayout(row)
        row2=QHBoxLayout()
        self.ratio=QComboBox();self.ratio.addItems(["1:1","4:5","4:3","3:2","16:9","9:16"]);row2.addWidget(self.ratio)
        x=QPushButton("Crop");x.clicked.connect(self.crop);row2.addWidget(x);lay.addLayout(row2)
        x=QPushButton("Auto AI Grade");x.clicked.connect(self.auto_grade);lay.addWidget(x)
        x=QPushButton("Match Reference...");x.clicked.connect(self.reference);lay.addWidget(x)
        row3=QHBoxLayout()
        x=QPushButton("Denoise");x.clicked.connect(lambda:self.enhance(0.35,1));row3.addWidget(x)
        x=QPushButton("2× Upscale");x.clicked.connect(lambda:self.enhance(0,2));row3.addWidget(x);lay.addLayout(row3)
        info=runtime_info()
        self.backend.setText(f"Runtime: {'CUDA / '+info.gpu_name if info.cuda else 'CPU'} | Detector: {'installed' if info.ultralytics else 'optional'}")

    def image(self):
        return self.window.document.original_image if self.window.document.has_image() else None
    def analyse(self):
        image=self.image()
        if image is None:return QMessageBox.information(self,"AI Studio","Open an image first.")
        self.progress.show();self.status.setText("Analysing photo with AI...");self.thread=QThread(self);self.worker=AIWorker(image.copy());self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run);self.worker.finished.connect(self.done);self.worker.error.connect(self.failed);self.worker.finished.connect(self.thread.quit);self.thread.start()
    @Slot(object)
    def done(self,result):
        self.progress.hide();self.status.setText(f"{result.scene} | Quality {result.quality_score:.0f}/100 | Faces {result.faces} | Sky {result.sky_fraction*100:.0f}% | {result.backend}")
        self.analysis_ready.emit(result)
    def failed(self,msg): self.progress.hide();self.status.setText("AI analysis unavailable; local fallbacks remain active.");QMessageBox.warning(self,"AI Studio",msg)
    def subject(self):
        image=self.image()
        if image is None:return
        try:self.mask_ready.emit(mask_to_local_adjustment(subject_mask(image),"AI Subject"))
        except Exception as e:QMessageBox.warning(self,"Subject Mask",str(e))
    def sky(self):
        image=self.image()
        if image is None:return
        try:self.mask_ready.emit(mask_to_local_adjustment(sky_mask(image),"AI Sky"))
        except Exception as e:QMessageBox.warning(self,"Sky Mask",str(e))
    def crop(self):
        image=self.image()
        if image is None:return
        w,h=map(float,self.ratio.currentText().split(":"));self.crop_ready.emit(smart_crop(image,w/h,True))
    def auto_grade(self):
        image=self.image()
        if image is None:return
        try:self.grade_ready.emit(analyze_image(image,True))
        except Exception as e:QMessageBox.warning(self,"AI Grade",str(e))
    def reference(self):
        image=self.image()
        if image is None:return
        path,_=QFileDialog.getOpenFileName(self,"Choose Reference Image","","Images (*.jpg *.jpeg *.png *.tif *.tiff *.webp)")
        if not path:return
        try:
            ref=__import__("PIL.Image",fromlist=["Image"]).Image.open(path).convert("RGB")
            sim=reference_similarity(image,ref);self.status.setText(f"Reference similarity: {sim*100:.1f}%")
            self.grade_ready.emit(reference_grade(image,ref))
        except Exception as e:QMessageBox.warning(self,"Reference Match",str(e))
    def enhance(self,denoise,scale): self.enhance_requested.emit(float(denoise),int(scale))
