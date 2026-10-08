from __future__ import annotations
from dataclasses import dataclass
from .analysis import analyze_image

@dataclass(frozen=True)
class Crop:
    left:float; top:float; right:float; bottom:float
    score:float

def smart_crop(image, aspect:float, use_ai=True)->Crop:
    a=analyze_image(image,use_ai=use_ai)
    w,h=image.size; target=aspect
    if w/h>target:
        crop_w=h*target; cx=.5
        if a.subject_box: cx=(a.subject_box[0]+a.subject_box[2])/2
        left=max(0,min(w-crop_w,cx*w-crop_w/2)); top=0
        return Crop(left/w,0,(left+crop_w)/w,1,a.composition_score)
    crop_h=w/target; cy=.5
    if a.subject_box: cy=(a.subject_box[1]+a.subject_box[3])/2
    top=max(0,min(h-crop_h,cy*h-crop_h/2)); left=0
    return Crop(0,top/h,1,(top+crop_h)/h,a.composition_score)
