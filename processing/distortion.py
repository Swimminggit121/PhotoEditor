from __future__ import annotations
from processing.lens_correction import apply_lens_correction

def apply_distortion(image, amount=0.0):
    return apply_lens_correction(image, amount, 0.0)
