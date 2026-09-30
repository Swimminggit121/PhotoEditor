from pathlib import Path
from PIL import Image

RAWS={".cr2",".cr3",".nef",".nrw",".arw",".srf",".sr2",".dng",".raf",".orf",".rw2",".pef",".srw",".3fr",".iiq",".rwl",".raw"}
RASTER={".jpg",".jpeg",".png",".tif",".tiff",".webp",".bmp",".gif"}
SUPPORTED_EXTENSIONS=RASTER|RAWS

def is_raw(path): return Path(path).suffix.lower() in RAWS
def is_supported(path): return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

def load_image(path):
    path=Path(path)
    if not is_supported(path): raise ValueError(f"Unsupported image format: {path.suffix}")
    if is_raw(path):
        try: import rawpy
        except ImportError as exc: raise RuntimeError("RAW support requires rawpy. Install it with: pip install rawpy") from exc
        with rawpy.imread(str(path)) as raw: rgb=raw.postprocess(use_camera_wb=True,output_bps=8,no_auto_bright=False)
        return Image.fromarray(rgb).convert("RGB")
    with Image.open(path) as im:return im.convert("RGB")
