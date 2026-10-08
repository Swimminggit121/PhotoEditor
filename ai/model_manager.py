from __future__ import annotations
import importlib.util, json
from pathlib import Path
from .config import MODEL_DIR, MODEL_SPECS, ModelSpec

class ModelManager:
    def __init__(self):
        self.manifest=MODEL_DIR/"manifest.json"
        self._data={}
        if self.manifest.exists():
            try:self._data=json.loads(self.manifest.read_text(encoding="utf-8"))
            except Exception:self._data={}
    def available(self,spec:ModelSpec)->bool:
        if spec.package=="ultralytics":
            return importlib.util.find_spec("ultralytics") is not None and (MODEL_DIR/spec.model_id).exists()
        if spec.package=="transformers":
            return importlib.util.find_spec("transformers") is not None
        if spec.package=="sentence-transformers":
            return importlib.util.find_spec("sentence_transformers") is not None
        return False
    def status(self):
        return {s.key:self.available(s) for s in MODEL_SPECS}
    def load_detector(self):
        if importlib.util.find_spec("ultralytics") is None:
            raise RuntimeError("AI detection requires the optional AI package. Install requirements-ai.txt.")
        from ultralytics import YOLO
        path=MODEL_DIR/"yolo26n.pt"
        model=YOLO(str(path) if path.exists() else "yolo26n.pt")
        if not path.exists():
            try:
                src=Path(model.ckpt_path)
                if src.exists(): src.replace(path)
            except Exception: pass
        return model
