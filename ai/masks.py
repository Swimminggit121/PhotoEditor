from __future__ import annotations
import cv2
import numpy as np
from .analysis import detect_sky, _rgb
from .model_manager import ModelManager

def sky_mask(image) -> np.ndarray:
    # Colour/position heuristic; not a learned semantic sky segmenter.
    return detect_sky(image)

def subject_mask(image) -> np.ndarray:
    """Use a DETR detection box as GrabCut guidance when possible.

    DETR supplies object boxes, not pixel-accurate segmentation masks.
    """
    a = _rgb(image)
    height, width = a.shape[:2]
    rect = None
    try:
        detections = ModelManager().load_detector().detect(a, threshold=0.35)
        if detections:
            best = max(detections, key=lambda item: item["confidence"] *
                       max(1e-6, item["box"][2] - item["box"][0]) *
                       max(1e-6, item["box"][3] - item["box"][1]))
            x1, y1, x2, y2 = best["box"]
            x, y = max(0, min(width - 1, int(x1 * width))), max(0, min(height - 1, int(y1 * height)))
            right, bottom = max(x + 1, min(width, int(x2 * width))), max(y + 1, min(height, int(y2 * height)))
            margin = max(1, int(min(width, height) * 0.015))
            left, top = max(0, x - margin), max(0, y - margin)
            right, bottom = min(width, right + margin), min(height, bottom + margin)
            if right - left >= 2 and bottom - top >= 2:
                rect = (left, top, right - left, bottom - top)
    except Exception:
        pass
    if rect is None:
        margin = max(2, int(min(height, width) * 0.08))
        rect = (margin, margin, max(2, width - 2 * margin), max(2, height - 2 * margin))
    x, y, w, h = rect
    if w >= width or h >= height:
        return np.zeros((height, width), dtype=np.uint8)
    mask = np.full((height, width), cv2.GC_BGD, np.uint8)
    mask[y:y+h, x:x+w] = cv2.GC_PR_FGD
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(a, mask, rect, bgd, fgd, 4, cv2.GC_INIT_WITH_RECT)
        return np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    except cv2.error:
        fallback = np.zeros((height, width), np.uint8)
        fallback[y:y+h, x:x+w] = 255
        return cv2.GaussianBlur(fallback, (0, 0), 2.0)

def mask_to_local_adjustment(mask, name="AI Subject"):
    return {"name": name, "type": "ai", "mask": mask.tolist(), "invert": False, "feather": 8,
            "density": 1.0, "local": {"exposure": 0.0, "contrast": 0.0, "temperature": 0.0, "saturation": 0.0}}
