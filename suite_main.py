import sys
from PySide6.QtWidgets import QApplication,QMainWindow,QTabWidget
from app.theme import apply_theme
from app.window import MainWindow
from video.editor import VideoEditorWindow
class SuiteWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle("PhotoEditor Suite");self.resize(1800,1000);self.setMinimumSize(1200,750)
        tabs=QTabWidget();self.photo_window=MainWindow();self.video_window=VideoEditorWindow();tabs.addTab(self.photo_window,"Photo Editor");tabs.addTab(self.video_window,"Video Editor");self.setCentralWidget(tabs)
    def closeEvent(self,event):
        self.photo_window.close();self.video_window.close();event.accept()
def main():
    app=QApplication(sys.argv);apply_theme(app);window=SuiteWindow();window.show();sys.exit(app.exec())
if __name__=="__main__":main()
