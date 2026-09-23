from pathlib import Path

from PIL import Image


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
    ".bmp",
}


def is_supported(path):
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def load_image(path):
    if not is_supported(path):
        raise ValueError(
            f"Unsupported image format: {Path(path).suffix}"
        )

    return Image.open(path).convert("RGB")