from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

APP_NAME = "PhotoEditor"
AI_DIR = Path(os.getenv("PHOTOEDITOR_AI_HOME", Path.home() / ".photoeditor" / "ai"))
MODEL_DIR = AI_DIR / "models"
CACHE_DIR = AI_DIR / "cache"

for p in (AI_DIR, MODEL_DIR, CACHE_DIR):
    p.mkdir(parents=True, exist_ok=True)

@dataclass(frozen=True)
class ModelSpec:
    key: str
    display_name: str
    package: str
    model_id: str
    size_mb: int
    purpose: str

MODEL_SPECS = (
    ModelSpec(
        "vision",
        "YOLO11 segmentation + object detection",
        "ultralytics",
        "yolo11n-seg.pt",
        6,
        "people, animals, vehicles, common objects and pixel-level subject masks",
    ),
    ModelSpec(
        "vision_large",
        "BLIP image understanding",
        "transformers",
        "Salesforce/blip-image-captioning-base",
        990,
        "optional semantic descriptions and richer scene understanding",
    ),
    ModelSpec(
        "embeddings",
        "CLIP visual embeddings",
        "transformers",
        "openai/clip-vit-base-patch32",
        600,
        "optional visual similarity, duplicate and reference matching",
    ),
)
