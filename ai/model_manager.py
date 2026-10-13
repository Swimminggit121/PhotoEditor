from __future__ import annotations
import importlib.util
import json
import threading
from typing import Any
from .config import AI_DIR, MODEL_SPECS, ModelSpec

class DETRDetector:
    """Adapter around the Apache-2.0-declared facebook/detr-resnet-50 model."""
    def __init__(self, processor: Any, model: Any, torch_module: Any, device: str):
        self.processor, self.model, self.torch, self.device = processor, model, torch_module, device
        self.model.eval()

    def detect(self, image, threshold: float = 0.30) -> list[dict[str, Any]]:
        import numpy as np
        from PIL import Image
        rgb = np.asarray(image.convert("RGB") if isinstance(image, Image.Image) else image)
        height, width = rgb.shape[:2]
        inputs = self.processor(images=Image.fromarray(rgb), return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with self.torch.inference_mode():
            outputs = self.model(**inputs)
        target_sizes = self.torch.tensor([(height, width)], device=self.device)
        results = self.processor.post_process_object_detection(
            outputs, threshold=threshold, target_sizes=target_sizes
        )[0]
        labels = self.model.config.id2label
        detections = []
        for score, label_id, box in zip(
            results["scores"].detach().cpu().tolist(),
            results["labels"].detach().cpu().tolist(),
            results["boxes"].detach().cpu().tolist(),
        ):
            x1, y1, x2, y2 = box
            detections.append({
                "label": str(labels.get(int(label_id), f"class_{label_id}")),
                "confidence": float(score),
                "box": (
                    max(0.0, min(1.0, x1 / width)),
                    max(0.0, min(1.0, y1 / height)),
                    max(0.0, min(1.0, x2 / width)),
                    max(0.0, min(1.0, y2 / height)),
                ),
            })
        return detections

class ModelManager:
    """Loads the optional local DETR model and records its source and terms."""
    _detector = None
    _detector_lock = threading.RLock()

    def __init__(self):
        self.manifest = AI_DIR / "manifest.json"
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

    def available(self, spec: ModelSpec) -> bool:
        try:
            return (
                importlib.util.find_spec("transformers") is not None
                and bool(self._data.get(spec.key, {}).get("downloaded", False))
            )
        except (ImportError, ValueError):
            return False

    def status(self):
        return {spec.key: self.available(spec) for spec in MODEL_SPECS}

    def ensure_detector(self) -> DETRDetector:
        with self._detector_lock:
            if ModelManager._detector is not None:
                return ModelManager._detector
            if importlib.util.find_spec("torch") is None or importlib.util.find_spec("transformers") is None:
                raise RuntimeError(
                    "The AI runtime is not installed. Install requirements-ai.txt or use the AI edition."
                )
            import torch
            from transformers import AutoImageProcessor, AutoModelForObjectDetection
            spec = MODEL_SPECS[0]
            processor = AutoImageProcessor.from_pretrained(spec.model_id)
            # Require SafeTensors so a legacy pickle checkpoint is never silently loaded.
            model = AutoModelForObjectDetection.from_pretrained(spec.model_id, use_safetensors=True)
            selected_device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(selected_device)
            detector = DETRDetector(processor, model, torch, selected_device)
            self._data[spec.key] = {
                "downloaded": True,
                "model": spec.model_id,
                "source": spec.source_url,
                "code_license": spec.code_license,
                "weights_license": spec.weights_license,
                "runtime_device": selected_device,
            }
            self._save()
            ModelManager._detector = detector
            return detector

    def load_detector(self):
        return self.ensure_detector()

    def preload_builtin_ai(self):
        return self.ensure_detector()
