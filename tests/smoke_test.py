import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from core.adjustment_stack import Adjustments
from core.document import Document
from core.renderer import Renderer
from core.auto_grade import auto_colour_grade
from core.project import save_project,load_project
from presets.manager import save_preset, list_presets, load_preset
from processing.montage import generate_reel_video
import tempfile
import wave
from pathlib import Path

image=Image.new("RGB",(160,100),(128,100,80))
a=Adjustments();a.exposure=5;a.contrast=10;a.texture=20;a.rotation=2;a.crop_left=.05;a.crop_right=.95
out=Renderer().render(image,a)
assert out.size[0]>0 and out.size[1]>0
graded=auto_colour_grade(image)
assert isinstance(graded,Adjustments)
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/"test.photoedit"
    x=Document();x.original_image=image;x.image=image;x.path=Path("test.jpg");x.adjustments=a;x.dirty=True
    save_project(x,p)
    y=Document();load_project(y,p)
    assert y.original_image.size==image.size

    preset_dir=Path(d)/"presets"; preset=save_preset(a,"smoke-preset",preset_dir/"preset.json");
    loaded=load_preset(preset)
    assert loaded.exposure==a.exposure
    assert preset.exists()
    assert len(list_presets()) >= 0

    reel_dir=Path(d)/"reel"; reel_dir.mkdir();
    frame=Image.new("RGB",(480,720),(10,20,30));
    photo=Path(reel_dir)/"shot1.jpg"; photo.write_bytes(b'')
    frame.save(photo)
    audio=Path(d)/"silence.wav"
    with wave.open(str(audio),"wb") as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(22050)
        stream.writeframes(b"\x00\x00"*22050)
    out=Path(d)/"montage.mp4"
    generate_reel_video(reel_dir, out, fps=8, duration_per_photo=.2, transition_duration=.1, aspect_ratio="9:16", audio_path=audio)
    assert out.exists() and out.stat().st_size > 0
print("PhotoEditor smoke test OK")
