from PIL import Image
from ai.analysis import analyze_image
from ai.runtime import runtime_info

img = Image.new("RGB", (320, 240), (120, 140, 170))
r = analyze_image(img, use_ai=False)

assert 0 <= r.quality_score <= 100
assert isinstance(runtime_info().gpu_name, str)
print("AI fallback tests OK")
