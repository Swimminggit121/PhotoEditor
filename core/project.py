from __future__ import annotations
import json,base64,io
from pathlib import Path
from PIL import Image
from core.adjustment_stack import Adjustments
PROJECT_VERSION=1
def save_project(document,path):
    path=Path(path)
    if not path.suffix:path=path.with_suffix(".photoedit")
    if document.original_image is None:raise ValueError("No image is open.")
    buf=io.BytesIO();document.original_image.save(buf,"PNG")
    data={"version":PROJECT_VERSION,"source_path":str(document.path) if document.path else None,"image_png":base64.b64encode(buf.getvalue()).decode("ascii"),"adjustments":document.adjustments.to_dict()}
    path.write_text(json.dumps(data,indent=2),encoding="utf-8");document.dirty=False;return path
def load_project(document,path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version")!=PROJECT_VERSION:raise ValueError("Unsupported .photoedit project version.")
    image=Image.open(io.BytesIO(base64.b64decode(data["image_png"]))).convert("RGB")
    document.original_image=image.copy();document.image=image.copy();document.path=Path(path)
    document.adjustments=Adjustments.from_dict(data.get("adjustments",{}));document.history.clear();document.history.push(document.adjustments);document.dirty=False;return document
