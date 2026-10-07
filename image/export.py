from pathlib import Path
from dataclasses import dataclass
from PIL import Image
from PIL import ImageCms
import numpy as np


@dataclass(frozen=True)
class ExportRecipe:
    key: str
    label: str
    extension: str
    quality: int
    max_dimension: int | None
    include_metadata: bool = False
    embed_srgb: bool = True
    bit_depth: int = 8


EXPORT_RECIPES = (
    ExportRecipe("web-jpeg", "Web JPEG · 2048 px", ".jpg", 90, 2048),
    ExportRecipe("print-jpeg", "Print JPEG · full size", ".jpg", 98, None),
    ExportRecipe("webp", "WebP · 2560 px", ".webp", 92, 2560),
    ExportRecipe("png", "PNG · full size", ".png", 100, None),
    ExportRecipe("tiff", "TIFF · full size", ".tif", 100, None),
    ExportRecipe("tiff-16", "16-bit TIFF · high-depth master", ".tif", 100, None, bit_depth=16),
)


def srgb_profile_bytes() -> bytes:
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def safe_export_path(path: str | Path) -> Path:
    path = Path(path).expanduser()
    if not path.exists():
        return path
    suffix = path.suffix
    for number in range(2, 10000):
        candidate = path.with_name(f"{path.stem}_{number}{suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Could not find an available export name for {path.name}.")


def export_image(
    image,
    path,
    quality=95,
    metadata=None,
    icc_profile=None,
    max_dimension=None,
    bit_depth=8,
):
    path=Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix=path.suffix.lower()
    if bit_depth not in (8, 16):
        raise ValueError("Image export bit depth must be 8 or 16.")
    if bit_depth == 16:
        if suffix not in {".tif", ".tiff"}:
            raise ValueError("16-bit master exports are supported as TIFF only.")
        if metadata:
            raise ValueError("Metadata embedding is not supported for 16-bit TIFF masters. Disable metadata or choose an 8-bit recipe.")
        pixels = np.asarray(image)
        if isinstance(image, Image.Image):
            pixels = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
        elif np.issubdtype(pixels.dtype, np.integer):
            pixels = pixels.astype(np.float32) / float(np.iinfo(pixels.dtype).max)
        else:
            pixels = pixels.astype(np.float32)
            if pixels.size and pixels.max() > 1:
                pixels = pixels / 255.0
        if pixels.ndim == 2:
            pixels = np.repeat(pixels[..., None], 3, axis=2)
        if pixels.ndim != 3 or pixels.shape[2] not in (3, 4):
            raise ValueError("16-bit TIFF export requires an RGB or RGBA image.")
        pixels = np.clip(pixels[..., :3], 0.0, 1.0)
        if max_dimension is not None:
            if int(max_dimension) <= 0:
                raise ValueError("Maximum export dimension must be a positive pixel count.")
            longest = max(pixels.shape[:2])
            if longest > int(max_dimension):
                import cv2
                scale = int(max_dimension) / longest
                pixels = cv2.resize(
                    pixels,
                    (max(1, int(pixels.shape[1] * scale)), max(1, int(pixels.shape[0] * scale))),
                    interpolation=cv2.INTER_LANCZOS4,
                )
        pixels = np.rint(pixels * 65535.0).astype(np.uint16)
        try:
            import tifffile
        except ImportError as exc:
            raise RuntimeError("16-bit TIFF export requires tifffile. Install the standard PhotoEditor requirements.") from exc
        tifffile.imwrite(
            path,
            pixels,
            photometric="rgb",
            compression="deflate",
            iccprofile=icc_profile,
            metadata=None,
        )
        return
    if not isinstance(image, Image.Image):
        pixels = np.asarray(image)
        if np.issubdtype(pixels.dtype, np.integer):
            pixels = pixels.astype(np.float32) / float(np.iinfo(pixels.dtype).max)
        else:
            pixels = pixels.astype(np.float32)
            if pixels.size and pixels.max() > 1:
                pixels = pixels / 255.0
        if pixels.ndim == 2:
            pixels = np.repeat(pixels[..., None], 3, axis=2)
        if pixels.ndim != 3 or pixels.shape[2] not in (3, 4):
            raise ValueError("Image export requires an RGB or RGBA image.")
        image = Image.fromarray(
            np.rint(np.clip(pixels[..., :3], 0, 1) * 255).astype(np.uint8),
            "RGB",
        )
    image=image.convert("RGB")
    if max_dimension is not None:
        if int(max_dimension) <= 0:
            raise ValueError("Maximum export dimension must be a positive pixel count.")
        if max(image.size) > int(max_dimension):
            image.thumbnail((int(max_dimension), int(max_dimension)), Image.Resampling.LANCZOS)
    kwargs={}
    if suffix in {".jpg",".jpeg"}: kwargs.update(format="JPEG",quality=max(1,min(100,int(quality))),optimize=True)
    elif suffix==".png": kwargs.update(format="PNG",optimize=True)
    elif suffix in {".tif",".tiff"}: kwargs.update(format="TIFF",compression="tiff_deflate")
    elif suffix==".webp": kwargs.update(format="WEBP",quality=max(1,min(100,int(quality))),method=6)
    else: raise ValueError(f"Unsupported export format: {suffix}")
    if metadata: kwargs["exif"]=metadata
    if icc_profile: kwargs["icc_profile"]=icc_profile
    image.save(path,**kwargs)


def export_with_recipe(image, path, recipe: ExportRecipe, metadata=None):
    if not isinstance(recipe, ExportRecipe):
        raise TypeError("A PhotoEditor ExportRecipe is required.")
    path = Path(path)
    if path.suffix.casefold() != recipe.extension:
        path = path.with_suffix(recipe.extension)
    if path.exists():
        path = safe_export_path(path)
    return export_image(
        image,
        path,
        quality=recipe.quality,
        metadata=metadata if recipe.include_metadata else None,
        icc_profile=srgb_profile_bytes() if recipe.embed_srgb else None,
        max_dimension=recipe.max_dimension,
        bit_depth=recipe.bit_depth,
    ) or path
