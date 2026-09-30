from PIL import Image
from core.adjustment_stack import Adjustments
from core.renderer import Renderer
from core.auto_grade import auto_colour_grade
from core.project import save_project,load_project
import tempfile
from pathlib import Path

image=Image.new("RGB",(160,100),(128,100,80))
a=Adjustments();a.exposure=5;a.contrast=10;a.texture=20;a.rotation=2;a.crop_left=.05;a.crop_right=.95
out=Renderer().render(image,a)
assert out.size[0]>0 and out.size[1]>0
graded=auto_colour_grade(image)
assert isinstance(graded,Adjustments)
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/"test.photoedit"
    class D:pass
    x=D();x.original_image=image;x.image=image;x.path=Path("test.jpg");x.adjustments=a;x.dirty=True
    class H:
        def clear(self):pass
        def push(self,x):pass
    x.history=H()
    save_project(x,p)
    y=D();y.history=H();load_project(y,p)
    assert y.original_image.size==image.size
print("PhotoEditor smoke test OK")
