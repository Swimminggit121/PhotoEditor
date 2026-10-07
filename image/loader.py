from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image
from PIL import ImageCms, ImageOps
from image.raw import load_raw_pixels

RAWS={".cr2",".cr3",".nef",".nrw",".arw",".srf",".sr2",".dng",".raf",".orf",".rw2",".pef",".srw",".3fr",".iiq",".rwl",".raw",".dcr",".kdc",".mrw",".x3f",".erf",".mef",".mos",".fff"}
RASTER={".jpg",".jpeg",".png",".tif",".tiff",".webp",".bmp",".gif"}
SUPPORTED_EXTENSIONS=RASTER|RAWS

def is_raw(path):
    return Path(path).suffix.lower() in RAWS

def is_supported(path):
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def _to_srgb(oriented):
    icc_profile = oriented.info.get("icc_profile")
    if not icc_profile:
        return oriented.convert("RGB")
    source_profile = ImageCms.ImageCmsProfile(BytesIO(icc_profile))
    target_profile = ImageCms.createProfile("sRGB")
    return ImageCms.profileToProfile(
        oriented, source_profile, target_profile, outputMode="RGB"
    )


def _is_srgb_profile(profile_bytes):
    if not profile_bytes:
        return True
    try:
        profile = ImageCms.ImageCmsProfile(BytesIO(profile_bytes))
        return "srgb" in ImageCms.getProfileDescription(profile).casefold()
    except (OSError, ValueError):
        return False


def _orient_array(array, orientation):
    if orientation == 2:
        return np.flip(array, axis=1)
    if orientation == 3:
        return np.rot90(array, 2)
    if orientation == 4:
        return np.flip(array, axis=0)
    if orientation == 5:
        return np.swapaxes(array, 0, 1)
    if orientation == 6:
        return np.rot90(array, -1)
    if orientation == 7:
        return np.flip(np.swapaxes(array, 0, 1), axis=(0, 1))
    if orientation == 8:
        return np.rot90(array, 1)
    return array


def _load_uint16_raster(path):
    import cv2

    encoded = np.fromfile(path, dtype=np.uint8)
    decoded = cv2.imdecode(encoded, cv2.IMREAD_UNCHANGED)
    if decoded is None or decoded.dtype != np.uint16:
        return None, None

    with Image.open(path) as source:
        icc_profile = source.info.get("icc_profile")
        if not _is_srgb_profile(icc_profile):
            return None, (
                "This 16-bit image uses a non-sRGB profile; it was color-converted "
                "with the existing 8-bit path. Convert it to sRGB to retain 16-bit editing."
            )
        try:
            orientation = source.getexif().get(274, 1)
        except (AttributeError, OSError):
            orientation = 1

    if decoded.ndim == 2:
        rgb = np.repeat(decoded[..., None], 3, axis=2)
    elif decoded.ndim == 3 and decoded.shape[2] == 4:
        rgb = cv2.cvtColor(decoded, cv2.COLOR_BGRA2RGB)
    elif decoded.ndim == 3 and decoded.shape[2] == 3:
        rgb = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)
    else:
        return None, None
    rgb = _orient_array(rgb, orientation)
    return (np.ascontiguousarray(rgb), icc_profile), None


def load_image_data(path):
    """Return an sRGB display image, optional 16-bit sRGB pixels, and a warning."""
    path = Path(path)
    if not is_supported(path):
        raise ValueError(f"Unsupported image format: {path.suffix}")
    if is_raw(path):
        pixels = load_raw_pixels(path)
        preview = (pixels / 257).round().astype(np.uint8)
        return Image.fromarray(preview, "RGB"), pixels, None

    high_depth, warning = _load_uint16_raster(path)
    if high_depth is not None:
        pixels, profile = high_depth
        preview = (pixels / 257).round().astype(np.uint8)
        return Image.fromarray(preview, "RGB"), pixels, None

    with Image.open(path) as im:
        oriented = ImageOps.exif_transpose(im)
        return _to_srgb(oriented), None, warning


def load_image(path):
    return load_image_data(path)[0]


def load_preview(path, max_dimension=1200):
    path = Path(path)
    if max_dimension <= 0:
        raise ValueError("Preview dimensions must be positive.")
    if is_raw(path):
        image = load_raw(path, half_size=True)
    else:
        with Image.open(path) as source:
            source.draft("RGB", (max_dimension, max_dimension))
            image = _to_srgb(ImageOps.exif_transpose(source))
    image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    return image
