from pathlib import Path

from PIL import Image


def export_image(image, path, quality=95):
    path = Path(path)

    suffix = path.suffix.lower()

    if suffix in {".jpg", ".jpeg"}:
        image.save(
            path,
            "JPEG",
            quality=quality,
            optimize=True
        )

    elif suffix == ".png":
        image.save(
            path,
            "PNG",
            optimize=True
        )

    elif suffix in {".tif", ".tiff"}:
        image.save(
            path,
            "TIFF"
        )

    elif suffix == ".webp":
        image.save(
            path,
            "WEBP",
            quality=quality
        )

    else:
        raise ValueError(
            f"Unsupported export format: {suffix}"
        )