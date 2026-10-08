from __future__ import annotations
import cv2, numpy as np
from PIL import Image

def local_retouch(image, mask, strength=0.25):
    a=np.asarray(image.convert("RGB"))
    m=np.asarray(mask,dtype=np.uint8)
    if m.shape[:2]!=a.shape[:2]: m=cv2.resize(m,(a.shape[1],a.shape[0]))
    smooth=cv2.bilateralFilter(a,9,35,35)
    alpha=(m.astype(np.float32)/255.0)*float(np.clip(strength,0,1))
    out=a*(1-alpha[...,None])+smooth*alpha[...,None]
    return Image.fromarray(np.uint8(np.clip(out,0,255)))
