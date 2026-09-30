from __future__ import annotations
import numpy as np

def apply_heal(image, center, radius=20.0, source=None, strength=1.0):
    a=np.asarray(image,dtype=np.float32).copy();h,w=a.shape[:2]
    cx,cy=float(center[0])*(w-1),float(center[1])*(h-1)
    sx,sy=(float(source[0])*(w-1),float(source[1])*(h-1)) if source else (cx+radius*2,cy)
    try:
        import cv2
        mask=np.zeros((h,w),np.uint8);cv2.circle(mask,(int(cx),int(cy)),max(1,int(radius)),255,-1)
        size=max(4,int(radius*2));patch=cv2.getRectSubPix(a,(size,size),(sx,sy))
        x0=max(0,int(cx-radius));y0=max(0,int(cy-radius));x1=min(w,x0+size);y1=min(h,y0+size)
        px0=max(0,size//2-(int(cx)-x0));py0=max(0,size//2-(int(cy)-y0))
        roi=a[y0:y1,x0:x1];src_patch=patch[py0:py0+roi.shape[0],px0:px0+roi.shape[1]]
        if roi.shape==src_patch.shape:
            m=(mask[y0:y1,x0:x1]/255.0)[...,None]*float(strength)
            a[y0:y1,x0:x1]=roi*(1-m)+src_patch*m
    except Exception:pass
    return np.clip(a,0,1)


def apply_retouch_spots(image, spots):
    out=np.asarray(image,dtype=np.float32).copy()
    for spot in spots or []:
        try:
            out=apply_heal(out,spot.get("center",[.5,.5]),spot.get("radius",20),spot.get("source"),spot.get("strength",1.0))
        except Exception:
            continue
    return np.clip(out,0,1)
