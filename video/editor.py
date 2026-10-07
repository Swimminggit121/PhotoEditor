from __future__ import annotations
from pathlib import Path
import cv2
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget

class VideoEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("PhotoEditor Video"); self.resize(1500,900); self.setMinimumSize(1000,650)
        self.capture=None; self.input_path=None; self.fps=30.0; self.frame_count=0; self.current_frame=0
        self.timer=QTimer(self); self.timer.timeout.connect(self.next_frame)
        self.preview=QLabel("Open a video to begin"); self.preview.setAlignment(Qt.AlignCenter); self.preview.setMinimumSize(640,360); self.preview.setStyleSheet("background:#111;color:#aaa;border:1px solid #333;")
        self.info=QLabel("Ready"); self.position=QSlider(Qt.Horizontal); self.position.setRange(0,0); self.position.sliderMoved.connect(self.seek)
        open_button=QPushButton("Open Video"); open_button.clicked.connect(self.open_video)
        self.play_button=QPushButton("Play"); self.play_button.clicked.connect(self.toggle_play)
        export_button=QPushButton("Export Video"); export_button.clicked.connect(self.export_video)
        controls=QHBoxLayout(); controls.addWidget(open_button); controls.addWidget(self.play_button); controls.addWidget(export_button); controls.addStretch()
        root=QVBoxLayout(); root.addWidget(self.preview,1); root.addWidget(self.position); root.addLayout(controls); root.addWidget(self.info)
        central=QWidget(); central.setLayout(root); self.setCentralWidget(central)

    def open_video(self):
        path,_=QFileDialog.getOpenFileName(self,"Open Video","", "Video Files (*.mp4 *.mov *.avi *.mkv *.m4v *.webm);;All Files (*)")
        if not path:return
        self.timer.stop()
        if self.capture is not None:self.capture.release()
        capture=cv2.VideoCapture(path)
        if not capture.isOpened():capture.release();QMessageBox.critical(self,"Could not open video","The video could not be decoded by OpenCV.");return
        self.capture=capture;self.input_path=Path(path);self.fps=max(1.0,float(capture.get(cv2.CAP_PROP_FPS) or 30.0));self.frame_count=max(1,int(capture.get(cv2.CAP_PROP_FRAME_COUNT)));self.current_frame=0
        self.position.setRange(0,self.frame_count-1);self.read_frame();self.info.setText(f"{self.input_path.name} | {self.frame_count} frames | {self.fps:.2f} FPS")

    def read_frame(self):
        if self.capture is None:return False
        self.capture.set(cv2.CAP_PROP_POS_FRAMES,self.current_frame);ok,frame=self.capture.read()
        if not ok:return False
        frame=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB);h,w,c=frame.shape
        image=QImage(frame.data,w,h,c*w,QImage.Format_RGB888).copy();pix=QPixmap.fromImage(image)
        self.preview.setPixmap(pix.scaled(self.preview.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
        self.position.blockSignals(True);self.position.setValue(self.current_frame);self.position.blockSignals(False);return True

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.capture is not None:self.read_frame()

    def toggle_play(self):
        if self.capture is None:return
        if self.timer.isActive():self.timer.stop();self.play_button.setText("Play")
        else:self.timer.start(max(1,int(1000/self.fps)));self.play_button.setText("Pause")

    def next_frame(self):
        if self.current_frame>=self.frame_count-1:self.timer.stop();self.play_button.setText("Play");return
        self.current_frame+=1;self.read_frame()

    def seek(self,frame):self.current_frame=int(frame);self.read_frame()

    def export_video(self):
        if self.capture is None or self.input_path is None:QMessageBox.information(self,"Export Video","Open a video first.");return
        path,_=QFileDialog.getSaveFileName(self,"Export Video",str(self.input_path.with_name(self.input_path.stem+"_edited.mp4")),"MP4 Video (*.mp4)")
        if not path:return
        self.timer.stop();self.play_button.setText("Play")
        source=cv2.VideoCapture(str(self.input_path))
        if not source.isOpened():QMessageBox.critical(self,"Export failed","The source video could not be reopened.");return
        width=int(source.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(source.get(cv2.CAP_PROP_FRAME_HEIGHT));fps=max(1.0,float(source.get(cv2.CAP_PROP_FPS) or 30.0))
        writer=cv2.VideoWriter(path,cv2.VideoWriter_fourcc(*"mp4v"),fps,(width,height))
        if not writer.isOpened():source.release();QMessageBox.critical(self,"Export failed","The MP4 encoder could not be opened on this system.");return
        processed=0
        try:
            while True:
                ok,frame=source.read()
                if not ok:break
                writer.write(frame);processed+=1
        finally:source.release();writer.release()
        self.info.setText(f"Exported: {Path(path).name} ({processed} frames)")
        QMessageBox.information(self,"Export complete",f"Video exported to:\n{path}")

    def closeEvent(self,event):
        self.timer.stop()
        if self.capture is not None:self.capture.release()
        event.accept()
