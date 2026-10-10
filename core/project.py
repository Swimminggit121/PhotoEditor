from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from PIL import Image
from core.adjustment_stack import Adjustments

PROJECT_VERSION = 3


def _image_bytes(image):
    if image is None:
        return None
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, "PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _decode_image(encoded):
    if not encoded:
        return None
    with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
        return image.convert("RGB").copy()


def save_project(document, path):
    path = Path(path)
    if not path.suffix:
        path = path.with_suffix(".photoedit")
    if document.original_image is None:
        raise ValueError("No image is open.")
    working = document.working_image if getattr(document, "working_image", None) is not None else document.original_image
    data = {
        "version": PROJECT_VERSION,
        "source_path": str(document.path) if document.path else None,
        # Keep image_png for compatibility with older project readers.
        "image_png": _image_bytes(document.original_image),
        "working_image_png": _image_bytes(working) if working is not document.original_image else None,
        "metadata_exif": base64.b64encode(getattr(document, "metadata", None)).decode("ascii") if getattr(document, "metadata", None) else None,
        "adjustments": document.adjustments.to_dict(),
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    document.dirty = False
    return path


def load_project(document, path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") not in (1, 2, PROJECT_VERSION):
        raise ValueError("Unsupported .photoedit project version.")

    source = _decode_image(data.get("image_png"))
    if source is None:
        raise ValueError("The project does not contain a readable source image.")
    working = _decode_image(data.get("working_image_png"))
    if working is None:
        working = source

    document.original_image = source
    document.working_image = working
    document.image = working
    document.path = path
    encoded_metadata = data.get("metadata_exif")
    try:
        document.metadata = base64.b64decode(encoded_metadata, validate=True) if encoded_metadata else None
    except Exception:
        document.metadata = None

    document.adjustments = Adjustments.from_dict(data.get("adjustments", {}))
    document.history.clear()
    if not hasattr(document, "_working_history"):
        document._working_history = {}
    else:
        document._working_history.clear()
    document.history.push(document.adjustments)
    document._working_history[document.history._index] = document.working_image
    if hasattr(document, "_preview_source"):
        document._preview_source = None
    if hasattr(document, "_original_preview_source"):
        document._original_preview_source = None
    for cache_name in ("render_cache", "preview_cache"):
        cache = getattr(document, cache_name, None)
        if cache is not None:
            cache.clear()
    document.dirty = False
    return document
