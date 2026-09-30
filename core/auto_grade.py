from __future__ import annotations
import numpy as np
from core.adjustment_stack import Adjustments

def auto_colour_grade(image, base=None):
    a=np.asarray(image.convert("RGB") if hasattr(image,"convert") else image,dtype=np.float32)
    if a.max()>1: a/=255.0
    a=np.clip(a[...,:3],0,1)
    lum=a[...,0]*.2126+a[...,1]*.7152+a[...,2]*.0722
    p1,p50,p99=np.percentile(lum,[1,50,99])
    mean=max(float(lum.mean()),.01)
    adj=base.copy() if base is not None else Adjustments()
    adj.exposure=float(np.clip(np.log2(.46/mean)*50,-35,35))
    adj.contrast=float(np.clip((.82-(p99-p1))*110,-25,25))
    adj.highlights=float(np.clip((.88-p99)*140,-35,35))
    adj.shadows=float(np.clip((.14-p1)*170,-35,35))
    adj.whites=float(np.clip((.94-p99)*80,-20,20))
    adj.blacks=float(np.clip((.06-p1)*80,-20,20))
    rgb=a.reshape(-1,3).mean(0)
    neutral=float(rgb.mean())
    adj.temperature=float(np.clip((rgb[2]-rgb[0])*-180,-30,30))
    adj.tint=float(np.clip((rgb[1]-neutral)*-220,-20,20))
    sat=float((a.max(-1)-a.min(-1)).mean())
    adj.vibrance=float(np.clip((.32-sat)*120,-10,28))
    adj.saturation=float(np.clip((.30-sat)*45,-8,10))
    return adj
