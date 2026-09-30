from pathlib import Path
from core.adjustment_stack import Adjustments
from core.history import History
from core.renderer import render_image
from image.loader import load_image
from core.performance import RenderCache
class Document:
    def __init__(self):
        self.image=None;self.original_image=None;self.path=None;self.adjustments=Adjustments();self.history=History();self.dirty=False;self.render_cache=RenderCache(6)
    def load(self,path):
        path=Path(path);image=load_image(path);self.original_image=image.copy();self.image=image.copy();self.path=path;self.adjustments.reset();self.history.clear();self.history.push(self.adjustments);self.dirty=False
    def render(self):
        if self.original_image is None:return None
        key=repr(self.adjustments.to_dict())
        cached=self.render_cache.get(key)
        if cached is not None:return cached.copy()
        result=render_image(self.original_image,self.adjustments)
        self.render_cache.put(key,result.copy())
        return result
    def push_history(self):self.history.push(self.adjustments);self.render_cache.clear();self.dirty=True
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
