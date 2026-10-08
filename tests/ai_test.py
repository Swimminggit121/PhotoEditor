from PIL import Image
from ai.analysis import analyze_image
from ai.runtime import runtime_info

img = Image.new("RGB", (320, 240), (120, 140, 170))
r = analyze_image(img, use_ai=False)
assert 0 <= r.quality_score <= 100
assert runtime_info().gpu_name is not None
print("AI fallback tests OK")
