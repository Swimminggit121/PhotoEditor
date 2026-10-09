from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import threading
from pathlib import Path

from .config import MODEL_DIR, MODEL_SPECS, ModelSpec


class ModelManager:
    """Central model loader with process-wide caching and safe first-run installation."""

    _detector = None
    _detector_lock = threading.RLock()

    def __init__(self):
        self.manifest = MODEL_DIR / "manifest.json"
        self._data = {}
        if self.manifest.exists():
            try:
                loaded = json.loads(self.manifest.read_text(encoding="utf-8"))
                self._data = loaded if isinstance(loaded, dict) else {}
            except (OSError, ValueError, TypeError):
                self._data = {}

    def _save(self):
        self.manifest.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.manifest.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        temporary.replace(self.manifest)

    def path(self, spec: ModelSpec) -> Path:
        return MODEL_DIR / Path(spec.model_id).name

    def _bundled_path(self, spec: ModelSpec) -> Path | None:
        if not getattr(sys, "frozen", False):
            return None
        root = Path(getattr(sys, "_MEIPASS", ""))
        candidate = root / "ai_bundle" / Path(spec.model_id).name
        return candidate if candidate.is_file() else None

    def _install_bundled_model(self, spec: ModelSpec) -> Path | None:
        bundled = self._bundled_path(spec)
        if bundled is None:
            return None
        target = self.path(spec)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or target.stat().st_size != bundled.stat().st_size:
            temporary = target.with_suffix(target.suffix + ".tmp")
            shutil.copy2(bundled, temporary)
            temporary.replace(target)
        self._data[spec.key] = {
            "downloaded": True,
            "model": spec.model_id,
            "source": "bundled",
            "size_bytes": target.stat().st_size,
        }
        self._save()
        return target

    def available(self, spec: ModelSpec) -> bool:
        if spec.package == "ultralytics":
            return importlib.util.find_spec("ultralytics") is not None and (
                self.path(spec).is_file() or self._bundled_path(spec) is not None
            )
        if spec.package == "transformers":
            return importlib.util.find_spec("transformers") is not None and bool(
                self._data.get(spec.key, {}).get("downloaded", False)
            )
        return False

    def status(self):
        return {spec.key: self.available(spec) for spec in MODEL_SPECS}

    def ensure_detector(self):
        with self._detector_lock:
            if ModelManager._detector is not None:
                return ModelManager._detector
            if importlib.util.find_spec("ultralytics") is None:
                raise RuntimeError(
                    "This copy of PhotoEditor does not include the AI runtime. "
                    "Download PhotoEditor-AI.exe from the official release for built-in AI features."
                )

            from ultralytics import YOLO

            spec = MODEL_SPECS[0]
            target = self._install_bundled_model(spec) or self.path(spec)
            if target.is_file():
                model = YOLO(str(target))
                source = "bundled" if self._bundled_path(spec) else "local"
            else:
                # Ultralytics downloads this official model into its own cache on first use.
                model = YOLO(spec.model_id)
                source = "ultralytics-cache"
                cached = Path(getattr(model, "ckpt_path", ""))
                if cached.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(cached, target)
                    except OSError:
                        pass

            self._data[spec.key] = {
                "downloaded": True,
                "model": spec.model_id,
                "source": source,
                "size_bytes": target.stat().st_size if target.is_file() else None,
            }
            self._save()
            ModelManager._detector = model
            return model

    def load_detector(self):
        return self.ensure_detector()

    def preload_builtin_ai(self):
        return self.ensure_detector()
