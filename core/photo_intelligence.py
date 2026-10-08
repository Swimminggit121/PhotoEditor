from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from image.loader import is_supported, load_image


@dataclass
class PhotoAnalysis:
    path: str
    width: int
    height: int
    brightness: float
    contrast: float
    sharpness: float
    exposure_score: float
    quality_score: float
    duplicate_group: int = -1
    duplicate_distance: int = 0
    faces: int = 0
    focal_x: float = 0.5
    focal_y: float = 0.5
    sky_fraction: float = 0.0


def _small(image: Image.Image, longest: int = 900) -> Image.Image:
    image = image.convert("RGB")
    if max(image.size) <= longest:
        return image
    scale = longest / max(image.size)
    return image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.BILINEAR)


def _phash(image: Image.Image) -> np.ndarray:
    gray = np.asarray(_small(image, 256).convert("L").resize((32, 32), Image.Resampling.BILINEAR), dtype=np.float32)
    dct = cv2.dct(gray)
    low = dct[:8, :8]
    median = np.median(low[1:, 1:])
    return (low > median).astype(np.uint8).flatten()


def hamming_distance(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.count_nonzero(a != b))


def detect_faces_and_focal(image: Image.Image) -> tuple[int, float, float]:
    small = _small(image, 900)
    gray = cv2.cvtColor(np.asarray(small), cv2.COLOR_RGB2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
    if len(faces):
        areas = [(w * h, x + w / 2, y + h / 2) for x, y, w, h in faces]
        area, x, y = max(areas)
        return len(faces), float(x / small.width), float(y / small.height)

    # Saliency gives a useful subject/focal estimate without requiring an ML model.
    if hasattr(cv2, "saliency"):
        saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
        ok, saliency_map = saliency.computeSaliency(np.asarray(small))
        if ok:
            _, _, _, max_loc = cv2.minMaxLoc(saliency_map)
            return 0, float(max_loc[0] / small.width), float(max_loc[1] / small.height)
    return 0, 0.5, 0.5


def estimate_sky_fraction(image: Image.Image) -> float:
    arr = np.asarray(_small(image, 700))
    if arr.size == 0:
        return 0.0
    h = arr.shape[0]
    upper = arr[: max(1, int(h * 0.45))]
    hsv = cv2.cvtColor(upper, cv2.COLOR_RGB2HSV)
    blue = ((hsv[:, :, 0] >= 85) & (hsv[:, :, 0] <= 135) &
            (hsv[:, :, 1] >= 35) & (hsv[:, :, 2] >= 80))
    return float(blue.mean())


def analyse_image(path: str | Path) -> PhotoAnalysis:
    path = Path(path)
    image = load_image(path)
    small = _small(image, 900)
    arr = np.asarray(small).astype(np.float32)
    gray = cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    brightness = float(gray.mean())
    contrast = float(gray.std())
    sharpness = float(cv2.Laplacian(gray, cv2.CV_32F).var())

    # Score exposure around the useful mid-range while penalising clipped pixels.
    under = float((gray < 12).mean())
    over = float((gray > 243).mean())
    mid = 1.0 - abs(brightness - 128.0) / 128.0
    exposure_score = max(0.0, min(100.0, 100.0 * (0.72 * mid + 0.28 * (1.0 - min(1.0, under + over)))))
    sharp_score = min(100.0, 100.0 * (np.log1p(sharpness) / np.log1p(600.0)))
    contrast_score = min(100.0, contrast * 2.2)
    quality = max(0.0, min(100.0, exposure_score * 0.38 + sharp_score * 0.42 + contrast_score * 0.20))
    try:
        faces, focal_x, focal_y = detect_faces_and_focal(small)
    except Exception:
        faces, focal_x, focal_y = 0, 0.5, 0.5
    try:
        sky_fraction = estimate_sky_fraction(small)
    except Exception:
        sky_fraction = 0.0
    return PhotoAnalysis(
        path=str(path),
        width=image.width,
        height=image.height,
        brightness=brightness,
        contrast=contrast,
        sharpness=sharpness,
        exposure_score=exposure_score,
        quality_score=quality,
        faces=faces,
        focal_x=focal_x,
        focal_y=focal_y,
        sky_fraction=sky_fraction,
    )


def analyse_folder(folder: str | Path, recursive: bool = True) -> list[PhotoAnalysis]:
    folder = Path(folder)
    iterator = folder.rglob("*") if recursive else folder.iterdir()
    paths = sorted(p for p in iterator if p.is_file() and is_supported(p))
    analyses = []
    hashes = []
    for path in paths:
        try:
            analysis = analyse_image(path)
            hashes.append(_phash(load_image(path)))
            analyses.append(analysis)
        except Exception:
            continue

    group = 0
    assigned: dict[int, int] = {}
    for i in range(len(analyses)):
        if i in assigned:
            analyses[i].duplicate_group = assigned[i]
            continue
        assigned[i] = group
        analyses[i].duplicate_group = group
        for j in range(i + 1, len(analyses)):
            if j in assigned:
                continue
            distance = hamming_distance(hashes[i], hashes[j])
            if distance <= 7:
                assigned[j] = group
                analyses[j].duplicate_group = group
                analyses[j].duplicate_distance = distance
        group += 1
    return analyses


class _RawContext:
    def __init__(self, path):
        self.path = path
        self.image = load_image(path)
    def __enter__(self): return self.image
    def __exit__(self, *args): self.image.close()


def _raw_context(path):
    return _RawContext(path)


def write_analysis_report(analyses: list[PhotoAnalysis], destination: str | Path) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(analyses[0]).keys()) if analyses else ["path"])
        writer.writeheader()
        for item in analyses:
            writer.writerow(asdict(item))
    return destination


def write_library_json(analyses: list[PhotoAnalysis], destination: str | Path) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if destination.exists():
        try:
            existing = json.loads(destination.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    payload = existing if isinstance(existing, dict) else {}
    for item in analyses:
        entry = payload.setdefault(item.path, {})
        entry.update({"quality_score": item.quality_score, "faces": item.faces, "focal_x": item.focal_x, "focal_y": item.focal_y})
        entry.setdefault("rating", 0)
        entry.setdefault("flag", "")
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def create_contact_sheet(analyses: list[PhotoAnalysis], destination: str | Path, columns: int = 4, thumb=(360, 240)) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    columns = max(1, int(columns))
    rows = max(1, (len(analyses) + columns - 1) // columns)
    cell_w, cell_h = thumb[0], thumb[1] + 54
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, analysis in enumerate(analyses):
        try:
            image = _small(load_image(analysis.path), max(thumb))
            image.thumbnail(thumb, Image.Resampling.LANCZOS)
            x = (index % columns) * cell_w + (cell_w - image.width) // 2
            y = (index // columns) * cell_h + 4
            sheet.paste(image, (x, y))
            label = f"{Path(analysis.path).name}\nScore {analysis.quality_score:.0f} | Faces {analysis.faces}"
            draw.multiline_text(((index % columns) * cell_w + 8, (index // columns) * cell_h + thumb[1] + 6), label, fill="black", spacing=2)
        except Exception:
            continue
    sheet.save(destination, format="JPEG", quality=94, optimize=True)
    return destination
