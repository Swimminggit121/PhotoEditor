import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from core.social_export import PROFILES,export_social_pack

def main():
    image=Image.new("RGB",(400,300),(80,120,160))
    root=Path("social_test_output")
    results=export_social_pack(image,"test",root,90)
    assert len(results)==len(PROFILES)
    for path in results:
        assert path.exists()
        with Image.open(path) as output:
            profile=next(p for p in PROFILES.values() if p.folder in path.parts)
            assert output.size==(profile.width,profile.height)
    import shutil
    shutil.rmtree(root,ignore_errors=True)
    print("SOCIAL EXPORT TEST OK")

if __name__=="__main__": main()
