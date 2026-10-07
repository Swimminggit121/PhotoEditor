import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tempfile import TemporaryDirectory
from PIL import Image
from core.adjustment_stack import Adjustments
from core.renderer import render_image
from core.document import Document
from core.project import save_project, load_project
from masks.manager import MaskManager
from masks.raster import rasterize_mask
from core.auto_grade import auto_edit


def main():
    image = Image.new("RGB", (160, 100), (120, 140, 160))
    a = Adjustments()
    a.exposure = 10
    assert render_image(image, a).size == (160, 100)

    a = Adjustments()
    a.crop_left = .1
    a.crop_top = .1
    a.crop_right = .9
    a.crop_bottom = .9
    assert render_image(image, a).size == (128, 80)

    a = Adjustments()
    a.local_adjustments.append(MaskManager.new_radial())
    a.local_adjustments[0]["local"]["exposure"] = 20
    mask = rasterize_mask(a.local_adjustments[0], (100, 160))
    assert mask.shape == (100, 160) and float(mask.max()) > 0
    assert render_image(image, a).size == (160, 100)

    auto = auto_edit(image)
    assert auto.curves_master and auto.grading_shadows["saturation"] > 0
    assert render_image(image, auto).size == (160, 100)

    with TemporaryDirectory() as tmp:
        d = Document()
        d.original_image = image.copy()
        d.image = image.copy()
        d.adjustments = a
        d._preview_source = None
        p = Path(tmp) / "roundtrip.photoedit"
        save_project(d, p)
        loaded = Document()
        load_project(loaded, p)
        assert loaded.adjustments.local_adjustments
        assert loaded.original_image.size == (160, 100)

    # Exercise the preview render/cache path from inside the test fixture scope.
    d = Document()
    d.original_image = image.copy()
    d._preview_source = None
    assert d.render(preview=True).size == (160, 100)
    assert d.render(preview=True).size == (160, 100)

    print("FEATURE TEST OK")


if __name__ == "__main__":
    main()
