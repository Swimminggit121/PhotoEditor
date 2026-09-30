from pathlib import Path
from PIL import Image
from image.raw import load_raw

RAWS={".cr2",".cr3",".nef",".nrw",".arw",".srf",".sr2",".dng",".raf",".orf",".rw2",".pef",".srw",".3fr",".iiq",".rwl",".raw",".dcr",".kdc",".mrw",".x3f",".erf",".mef",".mos",".fff"}
RASTER={".jpg",".jpeg",".png",".tif",".tiff",".webp",".bmp",".gif"}
SUPPORTED_EXTENSIONS=RASTER|RAWS

def is_raw(path):
    return Path(path).suffix.lower() in RAWS

def is_supported(path):
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

def load_image(path):
    path=Path(path)
    if not is_supported(path):
        raise ValueError(f"Unsupported image format: {path.suffix}")
    if is_raw(path):
        return load_raw(path)
    with Image.open(path) as im:
        return im.convert("RGB")
