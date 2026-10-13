import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from ai.analysis import analyze_image, quality_analysis
from ai.config import MODEL_SPECS
from ai.runtime import runtime_info

img = Image.new("RGB", (320, 240), (120, 140, 170))
result = analyze_image(img, use_ai=False)
info = runtime_info()

assert 0 <= result.quality_score <= 100
assert isinstance(info.gpu_name, str)
assert MODEL_SPECS[0].package == "transformers"
assert MODEL_SPECS[0].model_id == "facebook/detr-resnet-50"
assert len(MODEL_SPECS[0].revision) == 40
assert len(MODEL_SPECS[0].weights_sha256) == 64
assert all(character in "0123456789abcdef" for character in MODEL_SPECS[0].weights_sha256.lower())
assert "Apache-2.0" in MODEL_SPECS[0].weights_license
assert info.ultralytics is False
assert quality_analysis(img)["quality_score"] == result.quality_score

with tempfile.TemporaryDirectory() as directory:
    image_path = Path(directory) / "test.png"
    img.save(image_path)
    path_result = analyze_image(image_path, use_ai=False)
    assert 0 <= path_result.quality_score <= 100

print("AI fallback, image-path handling and pinned model metadata tests OK")
