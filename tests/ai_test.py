import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from ai.analysis import analyze_image
from ai.runtime import runtime_info

img = Image.new("RGB", (320, 240), (120, 140, 170))
result = analyze_image(img, use_ai=False)

assert 0 <= result.quality_score <= 100
assert isinstance(runtime_info().gpu_name, str)
print("AI fallback tests OK")
