from __future__ import annotations

import numpy as np
from PIL import Image

from core.adjustment_stack import Adjustments


def _clip01(value):
    return float(np.clip(value, -100.0, 100.0))


def _rgb(image):
    source=np.asarray(image.convert("RGB") if hasattr(image,"convert") else image)
    if np.issubdtype(source.dtype,np.integer):
        a=source.astype(np.float32)/float(np.iinfo(source.dtype).max)
    else:
        a=source.astype(np.float32)
        if a.size and a.max()>1: a/=255.0
    return np.clip(a[...,:3],0,1)


def _luma(a):
    return a[...,0]*0.2126+a[...,1]*0.7152+a[...,2]*0.0722


def _analysis_sample(image, max_size=1400):
    if isinstance(image, Image.Image):
        longest = max(image.size)
        if longest > max_size:
            scale = max_size / longest
            return image.resize(
                (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
                Image.Resampling.BILINEAR,
            )
    elif isinstance(image, np.ndarray) and image.ndim >= 2:
        longest = max(image.shape[:2])
        if longest > max_size:
            step = int(np.ceil(longest / max_size))
            return image[::step, ::step]
    return image


def _curve(points):
    return [(float(x),float(y)) for x,y in points]


def auto_colour_grade(image, base=None):
    a=_rgb(_analysis_sample(image))
    lum=_luma(a)
    p1,p5,p50,p95,p99=np.percentile(lum,[1,5,50,95,99])
    mean=float(lum.mean())
    rgb=a.reshape(-1,3).mean(0)
    neutral=float(rgb.mean())
    adj=base.copy() if base is not None else Adjustments()

    # Exposure and dynamic-range recovery.
    adj.exposure=float(np.clip(np.log2(0.46/max(mean,0.025))*50,-35,35))
    spread=max(p95-p5,0.05)
    adj.contrast=float(np.clip((0.72-spread)*95,-22,28))
    adj.highlights=float(np.clip((0.82-p95)*150,-45,35))
    adj.shadows=float(np.clip((0.16-p5)*180,-35,45))
    adj.whites=float(np.clip((0.93-p99)*75,-22,18))
    adj.blacks=float(np.clip((0.055-p1)*85,-18,22))

    # Automatic neutral balance. This is intentionally restrained so manual grading remains useful.
    adj.temperature=float(np.clip((rgb[2]-rgb[0])*-160,-28,28))
    adj.tint=float(np.clip((rgb[1]-neutral)*-180,-18,18))

    saturation=float((a.max(-1)-a.min(-1)).mean())
    adj.vibrance=float(np.clip((0.27-saturation)*105,-8,24))
    adj.saturation=float(np.clip((0.25-saturation)*32,-6,7))
    adj.texture=float(np.clip((0.20-spread)*45,-8,10))
    adj.clarity=float(np.clip((0.48-spread)*22,-5,8))
    adj.dehaze=float(np.clip((0.38-spread)*35,-4,12))
    adj.sharpening=float(np.clip(18+spread*35,10,42))
    adj.noise_reduction=float(np.clip((0.11-saturation)*20,0,8))
    adj.vignette=float(np.clip((0.48-mean)*18,0,12))

    # Gentle tonal curve: lift deep shadows, protect highlights and add a little midtone contrast.
    adj.curves_master=_curve([(0.0,0.015),(0.08,0.07),(0.25,0.23),(0.50,0.51),(0.75,0.78),(0.94,0.94),(1.0,0.985)])

    # Channel curves provide a subtle white-balance refinement without replacing the temperature control.
    rg=float(np.clip((rgb[0]-rgb[1])*0.08,-0.025,0.025))
    bg=float(np.clip((rgb[2]-rgb[1])*0.08,-0.025,0.025))
    adj.curves_red=_curve([(0,0),(0.25,0.25+rg),(0.5,0.5+rg),(0.75,0.75+rg),(1,1)])
    adj.curves_green=_curve([(0,0),(0.25,0.25),(0.5,0.5),(0.75,0.75),(1,1)])
    adj.curves_blue=_curve([(0,0),(0.25,0.25+bg),(0.5,0.5+bg),(0.75,0.75+bg),(1,1)])

    # Adaptive HSL: only make channels that actually exist in the image move.
    hsl={k:dict(v) for k,v in adj.hsl.items()}
    r,g,b=a[...,0],a[...,1],a[...,2]
    channels={
        "red":(r>g*1.18)&(r>b*1.18),
        "orange":(r>g*1.08)&(g>b*1.12)&(r>b*1.25),
        "yellow":(r>0.45)&(g>0.40)&(b<np.minimum(r,g)*0.78),
        "green":(g>r*1.10)&(g>b*1.05),
        "aqua":(g>b*0.98)&(b>r*1.05),
        "blue":(b>r*1.12)&(b>g*1.05),
        "purple":(b>g*1.08)&(r>b*0.82),
        "magenta":(r>b*1.05)&(b>g*1.12),
    }
    for name,mask in channels.items():
        coverage=float(mask.mean())
        if coverage<0.004: continue
        strength=float(np.clip(coverage*2.0,0.01,0.12))
        hsl[name]["saturation"]=float(np.clip(hsl[name]["saturation"]+strength*100*0.35,-12,12))
        if name in ("orange","yellow"):
            hsl[name]["hue"]=float(np.clip(hsl[name]["hue"]-strength*12,-8,8))
        elif name in ("aqua","blue"):
            hsl[name]["hue"]=float(np.clip(hsl[name]["hue"]-strength*8,-8,8))
    adj.hsl=hsl

    # Subtle cinematic colour separation: cooler shadows, warmer highlights.
    adj.grading_shadows={"hue":215.0,"saturation":float(np.clip(5+spread*7,4,10)),"luminance":0.0}
    adj.grading_midtones={"hue":42.0,"saturation":float(np.clip(1.5+abs(p50-0.5)*4,1,4)),"luminance":0.0}
    adj.grading_highlights={"hue":38.0,"saturation":float(np.clip(6+spread*8,5,12)),"luminance":0.0}
    adj.grading_global={"hue":38.0,"saturation":float(np.clip(1.0+saturation*3,1,4)),"luminance":0.0}
    adj.grading_blending=float(np.clip(42+spread*15,38,58))
    adj.grading_balance=float(np.clip((p50-0.5)*35,-12,12))
    return adj


def _profile_for_image(image, file_kind="generic"):
    if file_kind == "raw":
        return {
            "exposure": 10.0,
            "contrast": 12.0,
            "highlights": -10.0,
            "shadows": 18.0,
            "whites": 12.0,
            "blacks": -8.0,
            "texture": 10.0,
            "clarity": 10.0,
            "dehaze": 8.0,
            "sharpening": 22.0,
            "noise_reduction": 12.0,
            "vignette": 6.0,
        }
    if file_kind in {"jpeg", "png", "tif", "tiff", "webp"}:
        return {
            "exposure": 4.0,
            "contrast": 8.0,
            "highlights": -8.0,
            "shadows": 12.0,
            "whites": 6.0,
            "blacks": -4.0,
            "texture": 6.0,
            "clarity": 8.0,
            "dehaze": 4.0,
            "sharpening": 14.0,
            "noise_reduction": 6.0,
            "vignette": 4.0,
        }
    return {
        "exposure": 6.0,
        "contrast": 10.0,
        "highlights": -6.0,
        "shadows": 10.0,
        "whites": 8.0,
        "blacks": -6.0,
        "texture": 8.0,
        "clarity": 8.0,
        "dehaze": 6.0,
        "sharpening": 16.0,
        "noise_reduction": 8.0,
        "vignette": 5.0,
    }


def auto_professional_edit(image, base=None, file_kind="generic"):
    """Create a polished, production-ready develop style tuned for the input type."""
    adj = auto_colour_grade(image, base)
    profile = _profile_for_image(image, file_kind)

    for field, value in profile.items():
        if hasattr(adj, field):
            current = float(getattr(adj, field))
            setattr(adj, field, _clip01(current + value))

    if file_kind == "raw":
        adj.temperature = _clip01(adj.temperature + 8.0)
        adj.tint = _clip01(adj.tint + 4.0)
        adj.grading_blending = float(np.clip(adj.grading_blending + 8.0, 30.0, 65.0))
    elif file_kind in {"jpeg", "png", "tif", "tiff", "webp"}:
        adj.temperature = _clip01(adj.temperature + 4.0)
        adj.vibrance = _clip01(adj.vibrance + 6.0)
        adj.grading_blending = float(np.clip(adj.grading_blending + 4.0, 30.0, 65.0))
    else:
        adj.vibrance = _clip01(adj.vibrance + 2.0)

    return adj


def auto_edit(image, base=None, file_kind="generic"):
    """Create a complete restrained develop-grade from image statistics.

    The result is an ordinary Adjustments object, so every automatically chosen
    value remains editable in the normal Develop controls.
    """
    return auto_professional_edit(image, base, file_kind)
