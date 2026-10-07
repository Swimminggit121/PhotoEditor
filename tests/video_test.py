import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from video.editor import VideoEditorWindow

def main():
    assert VideoEditorWindow is not None
    print("VIDEO IMPORT TEST OK")

if __name__ == "__main__":
    main()
