from __future__ import annotations
import importlib.util
import json
import shutil
from pathlib import Path
from .config import MODEL_DIR, MODEL_SPECS, ModelSpec

class ModelManager:
    def __init__(self):
        self.manifest = MODEL_DIR / "manifest.json"
        self._data = {}
        if self.manifest.exists():
            try:
                self._data = json.loads(self.manifest.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    def _save(self):
        self.manifest.parent.mkdir(parents=True, exist_ok=True)
        self.manifest.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def path(self, spec: ModelSpec) -> Path:
        return MODEL_DIR / Path(spec.model_id).name

    def available(self, spec: ModelSpec) -> bool:
        if spec.package == "ultralytics":
            return importlib.util.find_spec("ultralytics") is not None and self.path(spec).exists()
        if spec.package == "transformers":
            # Hugging Face models are cached by transformers rather than copied into our model folder.
            return importlib.util.find_spec("transformers") is not None and bool(
                self._data.get(spec.key, {}).get("downloaded", False)
            )
        return False

    def status(self):
        return {s.key: self.available(s) for s in MODEL_SPECS}

    def ensure_detector(self):
        if importlib.util.find_spec("ultralytics") is None:
            raise RuntimeError(
                "The PhotoEditor AI build is required for AI detection. "
                "Please use PhotoEditor-AI.exe."
            )
        from ultralytics import YOLO
        spec = MODEL_SPECS[0]
        target = self.path(spec)
        target.parent.mkdir(parents=True, exist_ok=True)
        model = YOLO(str(target) if target.exists() else spec.model_id)
        if not target.exists():
            source = Path(getattr(model, "ckpt_path", ""))
            if source.exists():
                try:
                    shutil.copy2(source, target)
                except Exception:
                    pass
        self._data[spec.key] = {"downloaded": True, "model": spec.model_id}
        self._save()
        return model

    def load_detector(self):
        return self.ensure_detector()

    def preload_builtin_ai(self):
        # Used by the AI build's first-run bootstrap. If the model is already
        # bundled beside the executable this is instant; otherwise Ultralytics
        # downloads it once into the user's AI cache.
        return self.ensure_detector()
