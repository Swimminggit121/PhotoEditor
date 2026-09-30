from __future__ import annotations
import numpy as np
from PIL import Image
from core.adjustment_stack import Adjustments
from processing.hsl import apply_hsl
from processing.curves import apply_curves
from processing.colour_grading import apply_colour_grade
from processing.lens_correction import apply_lens_correction
from processing.healing import apply_retouch_spots
from masks.raster import rasterize_mask

def _array(image):
    if isinstance(image,Image.Image): return np.asarray(image.convert("RGB"),dtype=np.float32)/255.0
    a=np.asarray(image,dtype=np.float32)
    if a.ndim==2:a=np.repeat(a[...,None],3,axis=2)
    if a.shape[-1]==4:a=a[...,:3]
    if a.size and a.max()>1:a/=255.0
    return np.clip(a,0,1)

def _clip(a): return np.clip(a,0,1)
def _luma(a): return a[...,0]*.2126+a[...,1]*.7152+a[...,2]*.0722
def _exposure(a,v): return _clip(a*(2**(float(v)/50)))
def _contrast(a,v): return _clip((a-.5)*(1+float(v)/100)+.5)
def _highlights_shadows(a,h,s):
    l=_luma(a); hi=np.clip((l-.35)/.65,0,1)**1.5; sh=np.clip((.65-l)/.65,0,1)**1.5
    return _clip(a+hi[...,None]*float(h)/100*.28+sh[...,None]*float(s)/100*.28)
def _whites_blacks(a,w,b):
    l=_luma(a); wm=np.clip((l-.55)/.45,0,1)**1.5; bm=np.clip((.45-l)/.45,0,1)**1.5
    return _clip(a+wm[...,None]*float(w)/100*.22+bm[...,None]*float(b)/100*.22)
def _temperature(a,v):
    q=float(v)/100;x=a.copy();x[...,0]+=q*.1;x[...,1]+=q*.025;x[...,2]-=q*.1;return _clip(x)
def _tint(a,v):
    q=float(v)/100;x=a.copy();x[...,0]+=q*.045;x[...,1]-=q*.09;x[...,2]+=q*.045;return _clip(x)
def _saturation(a,v):
    l=_luma(a)[...,None];return _clip(l+(a-l)*(1+float(v)/100))
def _vibrance(a,v):
    q=float(v)/100;sat=a.max(-1)-a.min(-1);mean=a.mean(-1,keepdims=True);return _clip(a+(a-mean)*(1-sat)[...,None]*q*.8)
def _detail(a,texture,clarity,dehaze,sharp,noise):
    try:
        import cv2
        if texture or clarity or sharp:
            sigma=max(.35,2.0-(float(texture)+float(clarity)+float(sharp))/170)
            blur=cv2.GaussianBlur(a,(0,0),sigma); amount=(float(texture)*.35+float(clarity)*.55+float(sharp)*1.0)/100
            a=_clip(a+(a-blur)*amount)
        if noise:a=cv2.GaussianBlur(a,(0,0),min(5,max(.1,float(noise)/18)))
        if dehaze:
            l=_luma(a); a=_clip((a-l[...,None])*(1+float(dehaze)/180)+l[...,None]+float(dehaze)/100*.06)
    except Exception: pass
    return _clip(a)
def _grain(a,v):
    q=float(v)/100
    if q<=0:return a
    noise=np.random.default_rng(42).normal(0,q*.035,a.shape[:2])[...,None]
    return _clip(a+noise)
def _vignette(a,v):
    q=float(v)/100
    if abs(q)<.001:return a
    h,w=a.shape[:2];yy,xx=np.ogrid[:h,:w];x=(xx-(w-1)/2)/max((w-1)/2,1);y=(yy-(h-1)/2)/max((h-1)/2,1);r=np.sqrt(x*x+y*y);mask=np.clip((r-.25)/.75,0,1)**1.7
    return _clip(a*(1-q*.75*mask)[...,None])
def _local(a,adjustments):
    for mask in adjustments.local_adjustments:
        weights=rasterize_mask(mask,a.shape)
        if not np.any(weights):continue
        local=mask.get("local",{})
        original=a.copy()
        target=_exposure(original,float(local.get("exposure",0)))
        target=_contrast(target,float(local.get("contrast",0)))
        target=_temperature(target,float(local.get("temperature",0)))
        target=_tint(target,float(local.get("tint",0)))
        target=_saturation(target,float(local.get("saturation",0)))
        a=_clip(original*(1-weights[...,None])+target*weights[...,None])
    return a
def _transform(a,adj):
    out=Image.fromarray(np.round(_clip(a)*255).astype(np.uint8),"RGB")
    if adj.flip_horizontal:out=out.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if adj.flip_vertical:out=out.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if abs(adj.rotation)>.001:out=out.rotate(float(adj.rotation),resample=Image.Resampling.BICUBIC,expand=True,fillcolor=(0,0,0))
    w,h=out.size;l,t,r,b=adj.crop_left,adj.crop_top,adj.crop_right,adj.crop_bottom
    if (l,t,r,b)!=(0,0,1,1):
        box=(max(0,int(l*w)),max(0,int(t*h)),min(w,int(r*w)),min(h,int(b*h)))
        if box[2]>box[0] and box[3]>box[1]:out=out.crop(box)
    return out
def render_image(image,adjustments:Adjustments):
    original=image;a=_array(image)
    a=_exposure(a,adjustments.exposure);a=_contrast(a,adjustments.contrast)
    a=_highlights_shadows(a,adjustments.highlights,adjustments.shadows);a=_whites_blacks(a,adjustments.whites,adjustments.blacks)
    a=_temperature(a,adjustments.temperature);a=_tint(a,adjustments.tint)
    a=apply_hsl(a,adjustments.hsl);a=apply_curves(a,adjustments.curves_master,adjustments.curves_red,adjustments.curves_green,adjustments.curves_blue)
    a=_saturation(a,adjustments.saturation);a=_vibrance(a,adjustments.vibrance)
    a=apply_colour_grade(a,adjustments.grading_shadows,adjustments.grading_midtones,adjustments.grading_highlights,adjustments.grading_global,adjustments.grading_blending,adjustments.grading_balance)
    a=_detail(a,adjustments.texture,adjustments.clarity,adjustments.dehaze,adjustments.sharpening,adjustments.noise_reduction)
    a=apply_lens_correction(a,adjustments.lens_correction,adjustments.chromatic_aberration)
    a=apply_lens_correction(a,adjustments.distortion,0)
    a=_grain(a,adjustments.grain);a=_vignette(a,adjustments.vignette)
    a=_local(a,adjustments)
    a=apply_retouch_spots(a,adjustments.retouch_spots)
    out=_transform(a,adjustments)
    return out if isinstance(original,Image.Image) else np.asarray(out,dtype=np.float32)/255.0
class Renderer:
    def render(self,image,adjustments=None,masks=None,preview=False):return render_image(image,adjustments or Adjustments())
