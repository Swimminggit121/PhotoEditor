from __future__ import annotations
from PIL import Image

def crop(image,left,top,right,bottom):
    w,h=image.size; box=(max(0,int(left)),max(0,int(top)),min(w,int(right)),min(h,int(bottom)))
    return image.crop(box) if box[2]>box[0] and box[3]>box[1] else image.copy()

def rotate(image,angle,expand=True):
    return image.rotate(float(angle),resample=Image.Resampling.BICUBIC,expand=bool(expand),fillcolor=(0,0,0))

def flip_horizontal(image): return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
def flip_vertical(image): return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def straighten(image,angle): return rotate(image,angle,True)
def resize_fit(image,max_width=None,max_height=None):
    if not max_width and not max_height:return image.copy()
    w,h=image.size; scale=min((max_width/w if max_width else 1),(max_height/h if max_height else 1))
    if scale>=1:return image.copy()
    return image.resize((max(1,int(w*scale)),max(1,int(h*scale))),Image.Resampling.LANCZOS)
