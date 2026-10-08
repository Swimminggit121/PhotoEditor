from __future__ import annotations
import importlib.util
import json
import shutil
import sys
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

    def _bundled_path(self, spec: ModelSpec) -> Path | None:
        if not getattr(sys, "frozen", False):
            return None
        root = Path(getattr(sys, "_MEIPASS", ""))
        candidate = root / "ai_bundle" / Path(spec.model_id).name
        return candidate if candidate.exists() else None

    def _install_bundled_model(self, spec: ModelSpec) -> Path | None:
        bundled = self._bundled_path(spec)
        target = self.path(spec)
        if bundled is None:
            return None
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.stat().st_size != bundled.stat().st_size:
            shutil.copy2(bundled, target)
        self._data[spec.key] = {"downloaded": True, "model": spec.model_id, "source": "bundled"}
        self._save()
        return target

    def available(self, spec: ModelSpec) -> bool:
        if spec.package == "ultralytics":
            return importlib.util.find_spec("ultralytics") is not None and (
                self.path(spec).exists() or self._bundled_path(spec) is not None
            )
        if spec.package == "transformers":
            return importlib.util.find_spec("transformers") is not None and bool(
                self._data.get(spec.key, {}).get("downloaded", False)
            )
        return False

    def status(self):
        return {s.key: self.available(s) for s in MODEL_SPECS}

    def ensure_detector(self):
        if importlib.util.find_spec("ultralytics") is None:
            raise RuntimeError(
                "This copy of PhotoEditor does not include the AI runtime. "
                "Please use PhotoEditor-AI.exe for built-in AI features."
            )

        from ultralytics import YOLO

        spec = MODEL_SPECS[0]
        target = self._install_bundled_model(spec) or self.path(spec)
        model = YOLO(str(target)) if target.exists() else YOLO(spec.model_id)

        if not target.exists():
            source = Path(getattr(model, "ckpt_path", ""))
            if source.exists():
                try:
                    shutil.copy2(source, target)
                except Exception:
                    pass

        self._data[spec.key] = {
            "downloaded": True,
            "model": spec.model_id,
            "source": "local" if target.exists() else "ultralytics-cache",
        }
        self._save()
        return model

    def load_detector(self):
        return self.ensure_detector()

    def preload_builtin_ai(self):
        return self.ensure_detector()
