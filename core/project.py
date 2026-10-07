from __future__ import annotations
import base64, io, json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from core.adjustment_stack import Adjustments

PROJECT_VERSION=3

def save_project(document,path):
    path=Path(path)
    if not path.suffix:path=path.with_suffix(".photoedit")
    if document.original_image is None:raise ValueError("No image is open.")
    if document.native_pixels is not None:
        pixels = np.asarray(document.native_pixels)
        if pixels.dtype != np.uint16 or pixels.ndim != 3 or pixels.shape[2] != 3:
            raise ValueError("The high-depth source image cannot be saved in this project format.")
        success, encoded = cv2.imencode(
            ".png", cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)
        )
        if not success:
            raise OSError("Could not encode the 16-bit source image for the project.")
        image_data = {"image_png16": base64.b64encode(encoded).decode("ascii")}
    else:
        buf=io.BytesIO(); document.original_image.save(buf,"PNG")
        image_data = {"image_png":base64.b64encode(buf.getvalue()).decode("ascii")}
    data={"version":PROJECT_VERSION,"source_path":str(document.path) if document.path else None,**image_data,"adjustments":document.adjustments.to_dict()}
    path.write_text(json.dumps(data,indent=2),encoding="utf-8")
    document.dirty=False
    return path

def load_project(document,path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") not in (1,2,PROJECT_VERSION):raise ValueError("Unsupported .photoedit project version.")
    if "image_png16" in data:
        encoded = np.frombuffer(base64.b64decode(data["image_png16"]), dtype=np.uint8)
        decoded = cv2.imdecode(encoded, cv2.IMREAD_UNCHANGED)
        if decoded is None or decoded.dtype != np.uint16 or decoded.ndim != 3 or decoded.shape[2] != 3:
            raise ValueError("The high-depth source image in this project is invalid.")
        document.native_pixels = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)
        display = np.rint(document.native_pixels / 257).astype(np.uint8)
        image = Image.fromarray(display, "RGB")
        document.precision_warning = None
    else:
        image=Image.open(io.BytesIO(base64.b64decode(data["image_png"]))).convert("RGB")
        document.native_pixels = None
        document.precision_warning = None
    document.original_image=image.copy(); document.image=image.copy(); document.path=Path(path)
    document.adjustments=Adjustments.from_dict(data.get("adjustments",{}))
    document._preview_source=None
    document.render_cache.clear()
    document.preview_cache.clear()
    document.history.clear(); document.history.push(document.adjustments); document.dirty=False
    return document
