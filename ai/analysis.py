from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import cv2
import numpy as np
from PIL import Image
from .model_manager import ModelManager

@dataclass
class Detection:
    label: str
    confidence: float
    box: tuple[float, float, float, float]

@dataclass
class AIAnalysis:
    scene: str = "Unknown"
    detections: list[Detection] | None = None
    faces: int = 0
    subject_box: tuple[float, float, float, float] | None = None
    sky_fraction: float = 0.0
    quality_score: float = 0.0
    sharpness: float = 0.0
    noise_score: float = 0.0
    exposure_score: float = 0.0
    composition_score: float = 0.0
    suggestions: list[dict[str, Any]] | None = None
    backend: str = "heuristic"

def _rgb(image):
    if isinstance(image, (str, bytes, Path)):
        with Image.open(image) as opened:
            return np.asarray(opened.convert("RGB"))
    if hasattr(image, "convert"):
        return np.asarray(image.convert("RGB"))
    array = np.asarray(image)
    if array.ndim != 3 or array.shape[2] < 3:
        raise ValueError("Expected an RGB image, PIL image, or image file path.")
    return array[..., :3]

def quality_analysis(image) -> dict[str, float]:
    a = _rgb(image).astype(np.uint8, copy=False)
    gray = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY).astype(np.float32)
    lap = float(cv2.Laplacian(gray, cv2.CV_32F).var())
    sharp = float(np.clip(100 * np.log1p(lap) / np.log1p(900), 0, 100))
    noise = float(np.clip(100 / (1 + np.std(cv2.GaussianBlur(gray, (3, 3), 0) - gray)), 0, 100))
    mean = float(gray.mean())
    under, over = float((gray < 10).mean()), float((gray > 245).mean())
    exposure = float(np.clip(100 * (1 - abs(mean - 128) / 128) * (1 - min(1, under + over)), 0, 100))
    gx, gy = cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    composition = float(np.clip(np.percentile(np.hypot(gx, gy), 75) / 2.4, 0, 100))
    total = sharp * .42 + exposure * .35 + noise * .08 + composition * .15
    return {"quality_score": float(total), "sharpness": sharp, "noise_score": noise,
            "exposure_score": exposure, "composition_score": composition}

def detect_sky(image) -> np.ndarray:
    a = _rgb(image).astype(np.uint8, copy=False)
    h, s, v = cv2.split(cv2.cvtColor(a, cv2.COLOR_RGB2HSV))
    top = np.zeros(h.shape, np.uint8)
    cutoff = max(1, int(h.shape[0] * .55))
    blue = (h >= 85) & (h <= 135) & (s > 25) & (v > 70)
    top[:cutoff] = blue[:cutoff].astype(np.uint8) * 255
    n, labels, stats, _ = cv2.connectedComponentsWithStats(top)
    mask = np.zeros_like(top)
    for i in range(1, n):
        x, y, w, hh, area = stats[i]
        if y <= 2 and area > max(30, top.size // 5000):
            mask[labels == i] = 255
    return cv2.GaussianBlur(mask, (0, 0), 1.2)

def _detect_faces(gray):
    try:
        if not hasattr(cv2, "CascadeClassifier") or not hasattr(cv2, "data"):
            return []
        detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if detector.empty():
            return []
        return list(detector.detectMultiScale(gray, 1.1, 5, minSize=(28, 28)))
    except (AttributeError, cv2.error, OSError, TypeError):
        return []

def analyze_image(image, use_ai=True) -> AIAnalysis:
    q = quality_analysis(image)
    sky = float(detect_sky(image).mean() / 255)
    result = AIAnalysis(**q, sky_fraction=sky, suggestions=[])
    a = _rgb(image).astype(np.uint8, copy=False)
    gray = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    face_boxes = _detect_faces(gray)
    result.faces = len(face_boxes)
    detections: list[Detection] = []
    if use_ai:
        try:
            raw = ModelManager().load_detector().detect(a, threshold=0.30)
            detections = [Detection(item["label"], item["confidence"], tuple(item["box"])) for item in raw]
            result.backend = "detr+opencv"
        except Exception:
            # Model download/runtime failures must not prevent standard editing.
            result.backend = "opencv-fallback"
    result.detections = detections
    if detections:
        ranked = sorted(detections, key=lambda item: item.confidence *
                        max(0.0, item.box[2] - item.box[0]) * max(0.0, item.box[3] - item.box[1]), reverse=True)
        result.subject_box = ranked[0].box
    elif face_boxes:
        x, y, w, h = max(face_boxes, key=lambda item: item[2] * item[3])
        result.subject_box = (x / a.shape[1], y / a.shape[0], (x + w) / a.shape[1], (y + h) / a.shape[0])
    saturation = float(cv2.cvtColor(a, cv2.COLOR_RGB2HSV)[..., 1].mean())
    result.scene = "Landscape" if sky > .08 else ("Portrait" if face_boxes else
        ("Low light" if q["exposure_score"] < 45 else "General"))
    if q["exposure_score"] < 65:
        result.suggestions.append({"type": "exposure", "value": float(np.clip((50 - q["exposure_score"]) * .55, -25, 25))})
    if q["sharpness"] < 45:
        result.suggestions.append({"type": "sharpening", "value": 12.0})
    if sky > .08:
        result.suggestions.append({"type": "sky_mask", "value": sky})
    if saturation < 45:
        result.suggestions.append({"type": "vibrance", "value": 8.0})
    return result

def analysis_dict(result: AIAnalysis) -> dict:
    data = asdict(result)
    data["detections"] = [asdict(item) for item in (result.detections or [])]
    return data
