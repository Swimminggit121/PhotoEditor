from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

APP_NAME = "PhotoEditor"
AI_DIR = Path(os.getenv("PHOTOEDITOR_AI_HOME", Path.home() / ".photoeditor" / "ai"))
MODEL_DIR = AI_DIR / "models"
CACHE_DIR = AI_DIR / "cache"
for path in (AI_DIR, MODEL_DIR, CACHE_DIR):
    path.mkdir(parents=True, exist_ok=True)

@dataclass(frozen=True)
class ModelSpec:
    key: str
    display_name: str
    package: str
    model_id: str
    revision: str
    size_mb: int
    purpose: str
    code_license: str
    weights_license: str
    source_url: str

# Pin to an immutable upstream model revision instead of following mutable "main".
MODEL_SPECS = (
    ModelSpec(
        key="vision",
        display_name="DETR ResNet-50 object detection",
        package="transformers",
        model_id="facebook/detr-resnet-50",
        revision="1d5f47bd3bdd2c4bbfa585418ffe6da5028b4c0b",
        size_mb=170,
        purpose="COCO object detection for people, animals, vehicles and common objects",
        code_license="Apache-2.0 (Hugging Face Transformers)",
        weights_license="Apache-2.0 as declared by the official model repository; COCO dataset provenance remains a separate review item",
        source_url="https://huggingface.co/facebook/detr-resnet-50",
    ),
)
