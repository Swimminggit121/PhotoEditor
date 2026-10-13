import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from ai.analysis import analyze_image
from ai.config import MODEL_SPECS
from ai.runtime import runtime_info

img = Image.new("RGB", (320, 240), (120, 140, 170))
result = analyze_image(img, use_ai=False)
info = runtime_info()

assert 0 <= result.quality_score <= 100
assert isinstance(info.gpu_name, str)
assert MODEL_SPECS[0].package == "transformers"
assert MODEL_SPECS[0].model_id == "facebook/detr-resnet-50"
assert "Apache-2.0" in MODEL_SPECS[0].weights_license
assert info.ultralytics is False
print("AI fallback and model licence metadata tests OK")
