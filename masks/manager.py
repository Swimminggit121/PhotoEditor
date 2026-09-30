from __future__ import annotations
from copy import deepcopy

def _local():
    return {"exposure":0.0,"contrast":0.0,"temperature":0.0,"tint":0.0,"saturation":0.0}

class MaskManager:
    @staticmethod
    def new_brush(name="Brush Mask"):
        return {"name":name,"type":"brush","invert":False,"feather":0.0,"density":1.0,"strokes":[],"local":_local()}
    @staticmethod
    def new_linear(name="Linear Gradient"):
        return {"name":name,"type":"linear","invert":False,"feather":0.0,"density":1.0,"start":[0.0,0.0],"end":[1.0,1.0],"local":_local()}
    @staticmethod
    def new_radial(name="Radial Gradient"):
        return {"name":name,"type":"radial","invert":False,"feather":0.0,"density":1.0,"center":[0.5,0.5],"radius":[0.4,0.4],"local":_local()}
    @staticmethod
    def copy(mask):
        return deepcopy(mask)
