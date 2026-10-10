from __future__ import annotations

import importlib.util
import json
import os
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

    @staticmethod
    def _detector_paths(spec: ModelSpec):
        candidates = [
            MODEL_DIR / spec.model_id,
            Path.home() / ".config" / "Ultralytics" / "weights" / spec.model_id,
            Path.home() / ".cache" / "ultralytics" / spec.model_id,
        ]
        appdata = os.getenv("APPDATA")
        if appdata:
            candidates.extend([
                Path(appdata) / "Ultralytics" / "weights" / spec.model_id,
                Path(appdata) / "Ultralytics" / spec.model_id,
            ])
        return candidates

    @staticmethod
    def _has_hf_snapshot(model_id: str) -> bool:
        try:
            from huggingface_hub import try_to_load_from_cache
            model_path = model_id.replace("/", "--")
            cache_root = Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
            snapshot_root = cache_root / ("models--" + model_path) / "snapshots"
            return snapshot_root.is_dir() and any(p.is_dir() for p in snapshot_root.iterdir())
        except Exception:
            return False

    def available(self, spec: ModelSpec) -> bool:
        if spec.package == "ultralytics":
            return (
                importlib.util.find_spec("ultralytics") is not None
                and any(path.is_file() for path in self._detector_paths(spec))
            )
        if spec.package == "transformers":
            return (
                importlib.util.find_spec("transformers") is not None
                and self._has_hf_snapshot(spec.model_id)
            )
        if spec.package == "sentence-transformers":
            return (
                importlib.util.find_spec("sentence_transformers") is not None
                and self._has_hf_snapshot(spec.model_id)
            )
        return False

    def status(self):
        return {spec.key: self.available(spec) for spec in MODEL_SPECS}

    def load_detector(self):
        if importlib.util.find_spec("ultralytics") is None:
            raise RuntimeError(
                "AI detection requires the optional AI package. "
                "Install it with: python -m pip install -r requirements-ai.txt"
            )
        from ultralytics import YOLO

        spec = next(spec for spec in MODEL_SPECS if spec.key == "detector")
        local_path = next((path for path in self._detector_paths(spec) if path.is_file()), None)
        model = YOLO(str(local_path) if local_path else spec.model_id)

        # Remember the location chosen by Ultralytics when it downloaded weights.
        if local_path is None:
            try:
                checkpoint = getattr(model, "ckpt_path", None)
                if checkpoint and Path(checkpoint).is_file():
                    local_path = Path(checkpoint)
                if local_path is None:
                    for candidate in self._detector_paths(spec):
                        if candidate.is_file():
                            local_path = candidate
                            break
                if local_path is not None and local_path.resolve() != (MODEL_DIR / spec.model_id).resolve():
                    destination = MODEL_DIR / spec.model_id
                    if not destination.exists():
                        import shutil
                        shutil.copy2(local_path, destination)
            except (OSError, RuntimeError):
                # The model is still usable from its own cache even if copying fails.
                pass
        return model
