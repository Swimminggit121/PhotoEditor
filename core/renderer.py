from __future__ import annotations
import numpy as np
from PIL import Image
from core.adjustment_stack import Adjustments
from processing.hsl import apply_hsl
from processing.curves import apply_curves
from processing.colour_grading import apply_colour_grade

def _array(image):
    if isinstance(image, Image.Image):
        return np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    a=np.asarray(image,dtype=np.float32)
    if a.ndim==2: a=np.repeat(a[...,None],3,axis=2)
    if a.shape[-1]==4: a=a[...,:3]
    if a.size and a.max()>1: a/=255.0
    return np.clip(a,0,1)

def _clip(a): return np.clip(a,0,1)
def _luma(a): return a[...,0]*.2126+a[...,1]*.7152+a[...,2]*.0722
def _exposure(a,v): return _clip(a*(2.0**(float(v)/50.0)))
def _contrast(a,v):
    return _clip((a-.5)*(1.0+float(v)/100.0)+.5)
def _highlights_shadows(a,h,s):
    l=_luma(a); hi=np.clip((l-.35)/.65,0,1)**1.5; sh=np.clip((.65-l)/.65,0,1)**1.5
    return _clip(a+hi[...,None]*float(h)/100*.28+sh[...,None]*float(s)/100*.28)
def _whites_blacks(a,w,b):
    l=_luma(a); wm=np.clip((l-.55)/.45,0,1)**1.5; bm=np.clip((.45-l)/.45,0,1)**1.5
    return _clip(a+wm[...,None]*float(w)/100*.22+bm[...,None]*float(b)/100*.22)
def _temperature(a,v):
    x=a.copy(); q=float(v)/100; x[...,0]+=q*.10; x[...,1]+=q*.025; x[...,2]-=q*.10; return _clip(x)
def _tint(a,v):
    x=a.copy(); q=float(v)/100; x[...,0]+=q*.045; x[...,1]-=q*.09; x[...,2]+=q*.045; return _clip(x)
def _saturation(a,v):
    l=_luma(a)[...,None]; return _clip(l+(a-l)*(1+float(v)/100))
def _vibrance(a,v):
    q=float(v)/100; sat=a.max(-1)-a.min(-1); mean=a.mean(-1,keepdims=True)
    return _clip(a+(a-mean)*(1-sat)[...,None]*q*.8)
def _detail(a,sharp=0,noise=0):
    try:
        import cv2
        if sharp:
            blur=cv2.GaussianBlur(a,(0,0),max(.3,1.2-float(sharp)/140))
            a=_clip(a+(a-blur)*(float(sharp)/100*1.4))
        if noise:
            a=cv2.GaussianBlur(a,(0,0),min(9,max(0,float(noise)/12)))
    except Exception: pass
    return _clip(a)

def render_image(image, adjustments: Adjustments):
    original=image; a=_array(image)
    a=_exposure(a,adjustments.exposure); a=_contrast(a,adjustments.contrast)
    a=_highlights_shadows(a,adjustments.highlights,adjustments.shadows)
    a=_whites_blacks(a,adjustments.whites,adjustments.blacks)
    a=_temperature(a,adjustments.temperature); a=_tint(a,adjustments.tint)
    a=apply_hsl(a,adjustments.hsl)
    a=apply_curves(a,adjustments.curves_master,adjustments.curves_red,adjustments.curves_green,adjustments.curves_blue)
    a=_saturation(a,adjustments.saturation); a=_vibrance(a,adjustments.vibrance)
    a=apply_colour_grade(a,adjustments.grading_shadows,adjustments.grading_midtones,adjustments.grading_highlights,adjustments.grading_global,adjustments.grading_blending,adjustments.grading_balance)
    a=_detail(a,getattr(adjustments,"sharpening",0),getattr(adjustments,"noise_reduction",0))
    out=Image.fromarray(np.round(_clip(a)*255).astype(np.uint8),"RGB")
    return out if isinstance(original,Image.Image) else np.asarray(a,dtype=np.float32)

class Renderer:
    def render(self,image,adjustments=None,masks=None,preview=False):
        return render_image(image, adjustments or Adjustments())
