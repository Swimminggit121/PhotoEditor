from __future__ import annotations
import numpy as np

def _circle(h,w,cx,cy,radius,feather):
    yy,xx=np.ogrid[:h,:w]
    d=np.sqrt((xx-cx)**2+(yy-cy)**2)
    r=max(1.0,radius)
    inner=r*(1.0-max(0.0,min(1.0,feather)))
    return np.clip((r-d)/max(r-inner,1.0),0,1)

def rasterize_mask(mask,shape):
    h,w=shape[:2]
    kind=mask.get("type","brush")
    feather=float(mask.get("feather",0))/100
    density=float(mask.get("density",1))
    out=np.zeros((h,w),np.float32)
    if kind=="linear":
        sx,sy=mask.get("start",[0,0]); ex,ey=mask.get("end",[1,1])
        yy,xx=np.mgrid[0:h,0:w]; x=xx/max(w-1,1); y=yy/max(h-1,1)
        dx,dy=ex-sx,ey-sy; denom=max(dx*dx+dy*dy,1e-8)
        t=np.clip(((x-sx)*dx+(y-sy)*dy)/denom,0,1)
        out=1-t
        if feather: out=np.clip(out/(1-feather+1e-6),0,1)
    elif kind=="radial":
        cx,cy=mask.get("center",[.5,.5]); rx,ry=mask.get("radius",[.4,.4])
        yy,xx=np.mgrid[0:h,0:w]; x=xx/max(w-1,1); y=yy/max(h-1,1)
        d=np.sqrt(((x-cx)/max(rx,.001))**2+((y-cy)/max(ry,.001))**2)
        out=np.clip(1-d,0,1)
        if feather: out=np.clip((out-(1-feather))/max(feather,.001),0,1)
    else:
        for stroke in mask.get("strokes",[]):
            pts=stroke.get("points",[])
            radius=float(stroke.get("radius",30))/1000*max(w,h)
            for px,py in pts:
                out=np.maximum(out,_circle(h,w,float(px)*(w-1),float(py)*(h-1),radius,feather))
    if mask.get("invert"): out=1-out
    return np.clip(out*density,0,1)
