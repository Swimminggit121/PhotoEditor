from __future__ import annotations
from pathlib import Path
import cv2, numpy as np
from PIL import Image, ImageFilter

def denoise(image, strength=0.35):
    a=np.asarray(image.convert("RGB"))
    sigma=max(1.0,min(10.0,2.0+float(strength)*6))
    out=cv2.fastNlMeansDenoisingColored(a,None,sigma*3,sigma*3,7,21)
    return Image.fromarray(out)

def upscale(image, scale=2):
    scale=max(1,min(4,int(scale)))
    if scale==1:return image.copy()
    w,h=image.size
    # High-quality local fallback; the adapter can be replaced by a neural SR backend
    # without changing the UI or document pipeline.
    return image.resize((w*scale,h*scale),Image.Resampling.LANCZOS)

def enhance(image, denoise_strength=0.0, scale=1):
    out=image
    if denoise_strength>0: out=denoise(out,denoise_strength)
    if scale>1: out=upscale(out,scale)
    return out
