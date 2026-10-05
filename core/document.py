from pathlib import Path
from PIL import Image
from core.adjustment_stack import Adjustments
from core.history import History
from core.renderer import render_image
from image.loader import load_image
from core.performance import RenderCache
class Document:
    def __init__(self):
        self.image=None;self.original_image=None;self.path=None;self.adjustments=Adjustments();self.history=History();self.dirty=False;self.render_cache=RenderCache(2);self.preview_cache=RenderCache(3);self._preview_source=None
    def load(self,path):
        path=Path(path);image=load_image(path);self.original_image=image.copy();self.image=image.copy();self._preview_source=None;self.path=path;self.adjustments.reset();self.history.clear();self.history.push(self.adjustments);self.render_cache.clear();self.preview_cache.clear();self.dirty=False
    def preview_source(self):
        if self.original_image is None:return None
        if self._preview_source is not None:return self._preview_source
        image=self.original_image;longest=max(image.size)
        if longest<=1400:self._preview_source=image
        else:
            scale=1400/longest
            self._preview_source=image.resize((max(1,int(image.width*scale)),max(1,int(image.height*scale))),Image.Resampling.BILINEAR)
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
