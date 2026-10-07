import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
from core.adjustment_stack import Adjustments
from core.renderer import render_image
from core.document import Document, make_preview_source
from core.project import save_project, load_project
from image.export import export_image, srgb_profile_bytes
from masks.manager import MaskManager
from masks.raster import rasterize_mask
from core.auto_grade import auto_edit
from processing.hsl import CHANNELS, CHANNEL_HUES, apply_hsl, channel_weight, hsv_to_rgb_array, rgb_to_hsv_array
import numpy as np
import tifffile

def main():
    image=Image.new("RGB",(160,100),(120,140,160))
    a=Adjustments()
    a.exposure=10
    assert render_image(image,a).size==(160,100)

    a=Adjustments()
    a.crop_left=.1;a.crop_top=.1;a.crop_right=.9;a.crop_bottom=.9
    assert render_image(image,a).size==(128,80)

    a=Adjustments();a.local_adjustments.append(MaskManager.new_radial())
    a.local_adjustments[0]["local"]["exposure"]=20
    mask=rasterize_mask(a.local_adjustments[0],(100,160))
    assert mask.shape==(100,160) and float(mask.max())>0
    assert render_image(image,a).size==(160,100)

    auto=auto_edit(image)
    assert auto.curves_master and auto.grading_shadows["saturation"] > 0
    assert render_image(image,auto).size==(160,100)

    with TemporaryDirectory() as tmp:
        d=Document();d.original_image=image.copy();d.image=image.copy();d.adjustments=a;d._preview_source=None
        p=Path(tmp)/"roundtrip.photoedit";save_project(d,p)
        loaded=Document();load_project(loaded,p)
        assert loaded.adjustments.local_adjustments
        assert loaded.original_image.size==(160,100)

        red = Document();red.original_image=Image.new("RGB",(8,8),(255,0,0))
        blue = Document();blue.original_image=Image.new("RGB",(8,8),(0,0,255))
        red_path=Path(tmp)/"red.photoedit";blue_path=Path(tmp)/"blue.photoedit"
        save_project(red,red_path);save_project(blue,blue_path)
        switched=Document();load_project(switched,red_path)
        assert switched.render().getpixel((0,0))==(255,0,0)
        load_project(switched,blue_path)
        assert switched.render().getpixel((0,0))==(0,0,255)

    d=Document();d.original_image=image.copy();d._preview_source=None
    assert d.render(preview=True).size==(160,100)
    assert d.render(preview=True).size==(160,100)

    large=Image.new("RGB",(3000,2000),(120,140,160))
    d=Document();d.original_image=large
    assert d.render(preview=True).size==(1000,666)
    assert d.render().size==large.size

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        x = np.arange(256, dtype=np.uint16) * 96 + 4000
        gradient = np.broadcast_to(x, (48, 256))
        pixels = np.stack(
            (gradient, gradient + 800, gradient + 1600),
            axis=-1,
        ).copy()
        source = root / "gradient16.tif"
        tifffile.imwrite(source, pixels, photometric="rgb")

        high_depth = Document()
        high_depth.load(source)
        assert high_depth.native_pixels.dtype == np.uint16
        assert np.array_equal(high_depth.native_pixels, pixels)
        preview = make_preview_source(high_depth.native_pixels, 32)
        assert preview.shape[:2] == (6, 32)
        assert preview.dtype == np.uint16
        native = high_depth.render_master()
        assert native.dtype == np.float32
        assert np.allclose(native, pixels.astype(np.float32) / 65535.0)

        high_depth.adjustments.rotation = 2
        high_depth.adjustments.crop_left = 0.1
        high_depth.adjustments.crop_right = 0.9
        transformed = high_depth.render_master()
        assert transformed.shape[1] < pixels.shape[1]
        assert np.unique(np.rint(transformed[..., 0] * 65535)).size > 200

        master = root / "master16.tif"
        export_image(
            transformed,
            master,
            bit_depth=16,
            icc_profile=srgb_profile_bytes(),
        )
        exported = tifffile.imread(master)
        assert exported.dtype == np.uint16
        assert np.max(np.abs(exported.astype(np.int32) - np.rint(transformed * 65535).astype(np.int32))) <= 1
        with tifffile.TiffFile(master) as saved_master:
            assert saved_master.pages[0].tags.get(34675) is not None
        master_reopened = Document()
        master_reopened.load(master)
        assert master_reopened.native_pixels.dtype == np.uint16
        web_export = root / "web.jpg"
        export_image(transformed, web_export, quality=95)
        assert Image.open(web_export).size == (transformed.shape[1], transformed.shape[0])

        project = root / "high-depth.photoedit"
        save_project(high_depth, project)
        restored = load_project(Document(), project)
        assert np.array_equal(restored.native_pixels, pixels)
        assert np.allclose(restored.render_master(), transformed, atol=1e-6)

        eight_bit = Image.new("RGB", (4, 4), (12, 80, 190))
        eight_bit_output = render_image(eight_bit, Adjustments())
        assert eight_bit_output.getpixel((0, 0)) == (12, 80, 190)

    rng=np.random.default_rng(23)
    sample=rng.random((32,48,3),dtype=np.float32)
    hsl={key:{"hue":rng.uniform(-15,15),"saturation":rng.uniform(-12,12),"luminance":rng.uniform(-8,8)} for key in CHANNELS}
    hue,saturation,value=rgb_to_hsv_array(sample)
    old_hue=hue.copy();old_saturation=saturation.copy();old_value=value.copy()
    for channel in CHANNELS:
        settings=hsl[channel]
        weight=channel_weight(old_hue,CHANNEL_HUES[channel])
        hue+=weight*settings["hue"]
        saturation+=weight*settings["saturation"]/100
        value+=weight*settings["luminance"]/100
    old_result=hsv_to_rgb_array(hue%360,np.clip(saturation,0,1),np.clip(old_value+(value-old_value),0,1))
    new_result=apply_hsl(sample,hsl)
    assert np.allclose(new_result,old_result,atol=2e-6)
    print("FEATURE TEST OK")

if __name__=="__main__":
    main()
