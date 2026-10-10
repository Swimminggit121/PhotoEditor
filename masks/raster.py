from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image


def _circle(h, w, cx, cy, radius, feather):
    yy, xx = np.ogrid[:h, :w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    r = max(1.0, radius)
    inner = r * (1.0 - max(0.0, min(1.0, feather)))
    return np.clip((r - d) / max(r - inner, 1.0), 0, 1)


def _embedded_mask(mask, shape):
    """Decode compact PNG masks, while remaining compatible with older list masks."""
    encoded = mask.get("mask_png")
    raw = mask.get("mask")
    if encoded:
        try:
            payload = base64.b64decode(encoded, validate=True)
            with Image.open(io.BytesIO(payload)) as image:
                image = image.convert("L")
                target = (max(1, int(shape[1])), max(1, int(shape[0])))
                if image.size != target:
                    image = image.resize(target, Image.Resampling.BILINEAR)
                return np.asarray(image, dtype=np.float32) / 255.0
        except Exception:
            return None
    if raw is not None:
        try:
            arr = np.asarray(raw, dtype=np.float32)
            if arr.ndim == 2 and arr.size:
                if arr.max(initial=0) > 1:
                    arr = arr / 255.0
                image = Image.fromarray(np.uint8(np.clip(arr, 0, 1) * 255), "L")
                target = (max(1, int(shape[1])), max(1, int(shape[0])))
                if image.size != target:
                    image = image.resize(target, Image.Resampling.BILINEAR)
                return np.asarray(image, dtype=np.float32) / 255.0
        except Exception:
            return None
    return None


def rasterize_mask(mask, shape):
    h, w = shape[:2]
    kind = mask.get("type", "brush")
    feather = float(mask.get("feather", 0)) / 100
    density = float(mask.get("density", 1))
    embedded = _embedded_mask(mask, (h, w))
    if embedded is not None:
        out = embedded
    else:
        out = np.zeros((h, w), np.float32)
        if kind == "linear":
            sx, sy = mask.get("start", [0, 0])
            ex, ey = mask.get("end", [1, 1])
            yy, xx = np.mgrid[0:h, 0:w]
            x = xx / max(w - 1, 1)
            y = yy / max(h - 1, 1)
            dx, dy = ex - sx, ey - sy
            denom = max(dx * dx + dy * dy, 1e-8)
            t = np.clip(((x - sx) * dx + (y - sy) * dy) / denom, 0, 1)
            out = 1 - t
            if feather:
                out = np.clip(out / (1 - feather + 1e-6), 0, 1)
        elif kind == "radial":
            cx, cy = mask.get("center", [0.5, 0.5])
            rx, ry = mask.get("radius", [0.4, 0.4])
            yy, xx = np.mgrid[0:h, 0:w]
            x = xx / max(w - 1, 1)
            y = yy / max(h - 1, 1)
            d = np.sqrt(((x - cx) / max(rx, 0.001)) ** 2 + ((y - cy) / max(ry, 0.001)) ** 2)
            out = np.clip(1 - d, 0, 1)
            if feather:
                out = np.clip((out - (1 - feather)) / max(feather, 0.001), 0, 1)
        else:
            for stroke in mask.get("strokes", []):
                points = stroke.get("points", [])
                radius = float(stroke.get("radius", 30)) / 1000 * max(w, h)
                for px, py in points:
                    out = np.maximum(out, _circle(h, w, float(px) * (w - 1), float(py) * (h - 1), radius, feather))
    if mask.get("invert"):
        out = 1 - out
    return np.clip(out * density, 0, 1)
