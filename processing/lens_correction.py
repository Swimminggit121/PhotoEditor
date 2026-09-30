from __future__ import annotations
import numpy as np

def apply_lens_correction(image, amount=0.0, chromatic=0.0):
    amount=float(amount); chromatic=float(chromatic)
    if abs(amount)<1e-6 and abs(chromatic)<1e-6:return image
    try:
        import cv2
        a=np.asarray(image,dtype=np.float32)
        h,w=a.shape[:2]
        yy,xx=np.mgrid[0:h,0:w]; x=(xx-(w-1)/2)/max((w-1)/2,1); y=(yy-(h-1)/2)/max((h-1)/2,1)
        r2=x*x+y*y; k=amount/1000.0
        factor=1+k*r2
        mx=((x*factor+1)*.5*(w-1)).astype(np.float32); my=((y*factor+1)*.5*(h-1)).astype(np.float32)
        out=cv2.remap(a,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
        if abs(chromatic)>1e-6:
            c=chromatic/1000.0
            for channel,sign in ((0,-1),(2,1)):
                f=1+sign*c*r2
                cx=((x*f+1)*.5*(w-1)).astype(np.float32); cy=((y*f+1)*.5*(h-1)).astype(np.float32)
                out[...,channel]=cv2.remap(a[...,channel],cx,cy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
        return np.clip(out,0,1)
    except Exception:
        return image
