from __future__ import annotations

import base64
import io

import cv2
import numpy as np
from PIL import Image

from .analysis import detect_sky, _rgb
from .model_manager import ModelManager
from .runtime import device


def sky_mask(image) -> np.ndarray:
    return detect_sky(image)


def subject_mask(image) -> np.ndarray:
    a = _rgb(image)
    h, w = a.shape[:2]
    try:
        model = ModelManager().load_detector()
        result = model(a, device=device(), verbose=False)[0]
        if result.masks is not None and len(result.masks.data) and result.boxes is not None:
            scores = [float(x) for x in result.boxes.conf]
            index = int(np.argmax(scores))
            mask = result.masks.data[index].cpu().numpy()
            return cv2.resize((mask > 0.35).astype(np.uint8) * 255, (w, h), interpolation=cv2.INTER_NEAREST)
    except Exception:
        # AI is optional: fall back to a local classical segmentation method.
        pass

    if min(h, w) < 8:
        return np.full((h, w), 255, dtype=np.uint8)
    margin = max(1, int(min(h, w) * 0.08))
    rect_w, rect_h = max(1, w - 2 * margin), max(1, h - 2 * margin)
    mask = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    mask[margin:h - margin, margin:w - margin] = cv2.GC_PR_FGD
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(a, mask, (margin, margin, rect_w, rect_h), bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
        return np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    except Exception:
        # Never fail the UI because an image is too small or pathological.
        fallback = np.zeros((h, w), np.uint8)
        fallback[margin:max(margin + 1, h - margin), margin:max(margin + 1, w - margin)] = 255
        return fallback


def mask_to_local_adjustment(mask, name="AI Subject"):
    """Serialize a mask as PNG bytes rather than a huge nested list of pixels."""
    array = np.asarray(mask)
    if array.ndim != 2:
        raise ValueError("An AI mask must be a two-dimensional grayscale array.")
    image = Image.fromarray(np.uint8(np.clip(array, 0, 255)), "L")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "name": name,
        "type": "ai",
        "mask_png": encoded,
        "invert": False,
        "feather": 8,
        "density": 1.0,
        "local": {"exposure": 0.0, "contrast": 0.0, "temperature": 0.0, "tint": 0.0, "saturation": 0.0},
    }
