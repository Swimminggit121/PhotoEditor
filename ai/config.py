from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

APP_NAME="PhotoEditor"
AI_DIR=Path(os.getenv("PHOTOEDITOR_AI_HOME", Path.home()/".photoeditor"/"ai"))
MODEL_DIR=AI_DIR/"models"
CACHE_DIR=AI_DIR/"cache"
for p in (AI_DIR, MODEL_DIR, CACHE_DIR):
    p.mkdir(parents=True, exist_ok=True)

@dataclass(frozen=True)
class ModelSpec:
    key:str
    display_name:str
    package:str
    model_id:str
    size_mb:int
    purpose:str

MODEL_SPECS=(
    ModelSpec("detector","Object & subject detection","ultralytics","yolo11n-seg.pt",12,"people, animals, vehicles and common objects"),
    ModelSpec("vision","Image understanding","transformers","Salesforce/blip-image-captioning-base",990,"scene and semantic descriptions"),
    ModelSpec("embeddings","Visual embeddings","sentence-transformers","clip-ViT-B-32",350,"duplicate and reference matching"),
)
