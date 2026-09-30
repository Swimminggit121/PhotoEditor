from pathlib import Path
from PIL import Image
from core.adjustment_stack import Adjustments
from core.history import History
from core.renderer import render_image
from image.loader import load_image
from core.performance import RenderCache
class Document:
    def __init__(self):
        self.image=None;self.original_image=None;self.path=None;self.adjustments=Adjustments();self.history=History();self.dirty=False;self.render_cache=RenderCache(2);self.preview_cache=RenderCache(3)
    def load(self,path):
        path=Path(path);image=load_image(path);self.original_image=image.copy();self.image=image.copy();self.path=path;self.adjustments.reset();self.history.clear();self.history.push(self.adjustments);self.render_cache.clear();self.preview_cache.clear();self.dirty=False
    def _preview_source(self):
        image=self.original_image
        if image is None:return None
        longest=max(image.size)
        if longest<=1400:return image
        scale=1400/longest
        return image.resize((max(1,int(image.width*scale)),max(1,int(image.height*scale))),Image.Resampling.BILINEAR)

    def render(self,preview=False):
        if self.original_image is None:return None
        cache=self.preview_cache if preview else self.render_cache
        key=(preview,repr(self.adjustments.to_dict()))
        cached=cache.get(key)
        if cached is not None:return cached.copy()
        source=self._preview_source() if preview else self.original_image
        result=render_image(source,self.adjustments)
        cache.put(key,result.copy())
        return result
    def push_history(self):self.history.push(self.adjustments);self.render_cache.clear();self.preview_cache.clear();self.dirty=True
    def set_adjustment(self,name,value,add_history=True):
        if not hasattr(self.adjustments,name):raise AttributeError(f"Unknown adjustment: {name}")
        setattr(self.adjustments,name,float(value));self.render_cache.clear();self.dirty=True
        if add_history:self.push_history()
    def undo(self):
        state=self.history.undo()
        if state is None:return False
        self.adjustments=state;self.dirty=True;return True
    def redo(self):
        state=self.history.redo()
        if state is None:return False
        self.adjustments=state;self.dirty=True;return True
    def reset_adjustments(self):self.adjustments.reset();self.render_cache.clear();self.push_history()
    def has_image(self):return self.original_image is not None
