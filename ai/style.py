from __future__ import annotations
import numpy as np
from PIL import Image
from core.auto_grade import auto_colour_grade

def histogram_signature(image,bins=32):
    a=np.asarray(image.convert("RGB"),dtype=np.float32)/255
    return np.concatenate([np.histogram(a[...,i],bins=bins,range=(0,1),density=True)[0] for i in range(3)])

def reference_similarity(source,reference):
    a=histogram_signature(source); b=histogram_signature(reference)
    return float(1/(1+np.mean(np.abs(a-b))))

def reference_grade(source,reference):
    # Stable, local, dependency-free approximation: compare channel means/stds.
    a=np.asarray(source.convert("RGB"),dtype=np.float32); b=np.asarray(reference.convert("RGB"),dtype=np.float32)
    am=a.mean((0,1)); bm=b.mean((0,1)); ast=a.std((0,1)); bst=b.std((0,1))
    adj=auto_colour_grade(source)
    adj.temperature=float(np.clip((bm[2]-bm[0])-(am[2]-am[0]),-28,28))
    adj.tint=float(np.clip((bm[1]-bm[0])-(am[1]-am[0]),-18,18))
    adj.contrast=float(np.clip((bst.mean()-ast.mean())*.7,-20,20))
    adj.saturation=float(np.clip((bm.mean()-am.mean())*.25,-12,12))
    return adj
