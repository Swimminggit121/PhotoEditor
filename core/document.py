from pathlib import Path
import numpy as np
from PIL import Image
from core.adjustment_stack import Adjustments
from core.history import History
from core.renderer import render_image
from image.loader import load_image_data
from core.performance import RenderCache

def make_preview_source(image,max_size):
    if isinstance(image, np.ndarray):
        height, width = image.shape[:2]
        longest = max(width, height)
        if longest <= max_size:
            return image
        scale = max_size / longest
        import cv2
        return cv2.resize(
            image,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
    longest=max(image.size)
    if longest<=max_size:return image
    scale=max_size/longest
    return image.resize((max(1,int(image.width*scale)),max(1,int(image.height*scale))),Image.Resampling.BILINEAR)

class Document:
    def __init__(self):
        self.image=None;self.original_image=None;self.native_pixels=None;self.precision_warning=None;self.path=None;self.adjustments=Adjustments();self.history=History();self.dirty=False;self.render_cache=RenderCache(2);self.preview_cache=RenderCache(3);self._preview_source=None;self.preview_max_size=1000
    def load(self,path):
        path=Path(path);image,pixels,warning=load_image_data(path);self.original_image=image.copy();self.image=image.copy();self.native_pixels=pixels;self.precision_warning=warning;self._preview_source=None;self.path=path;self.adjustments.reset();self.history.clear();self.history.push(self.adjustments);self.render_cache.clear();self.preview_cache.clear();self.dirty=False
    def preview_source(self):
        if self.original_image is None:return None
        if self._preview_source is not None:return self._preview_source
        self._preview_source=make_preview_source(self.original_image,self.preview_max_size)
        return self._preview_source

    def render(self,preview=False):
        if self.original_image is None:return None
        cache=self.preview_cache if preview else self.render_cache
        key=(preview,repr(self.adjustments.to_dict()))
        cached=cache.get(key)
        if cached is not None:return cached
        source=self.preview_source() if preview else self.original_image
        result=render_image(source,self.adjustments)
        cache.put(key,result)
        return result
    def render_master(self):
        if self.original_image is None:return None
        if self.native_pixels is None:return self.render()
        key=("master",repr(self.adjustments.to_dict()))
        cached=self.render_cache.get(key)
        if cached is not None:return cached
        result=render_image(self.native_pixels,self.adjustments)
        self.render_cache.put(key,result)
        return result
    @property
    def analysis_image(self):
        return self.native_pixels if self.native_pixels is not None else self.original_image
    def push_history(self):self.history.push(self.adjustments);self.render_cache.clear();self.preview_cache.clear();self.dirty=True
    def set_adjustment(self,name,value,add_history=True):
        if not hasattr(self.adjustments,name):raise AttributeError(f"Unknown adjustment: {name}")
        setattr(self.adjustments,name,float(value));self.render_cache.clear();self.preview_cache.clear();self.dirty=True
        if add_history:self.push_history()
    def undo(self):
        state=self.history.undo()
        if state is None:return False
        self.adjustments=state;self.render_cache.clear();self.preview_cache.clear();self.dirty=True;return True
    def redo(self):
        state=self.history.redo()
        if state is None:return False
        self.adjustments=state;self.render_cache.clear();self.preview_cache.clear();self.dirty=True;return True
    def reset_adjustments(self):self.adjustments.reset();self.render_cache.clear();self.push_history()
    def has_image(self):return self.original_image is not None
