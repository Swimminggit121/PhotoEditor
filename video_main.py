import sys
from PySide6.QtWidgets import QApplication
from video.application import VideoEditorApplication
def main():
    app=QApplication(sys.argv);editor=VideoEditorApplication();editor.show();sys.exit(app.exec())
if __name__=="__main__":main()
