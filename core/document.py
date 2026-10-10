from __future__ import annotations

from pathlib import Path

from PIL import Image

from core.adjustment_stack import Adjustments
from core.history import History
from core.renderer import render_image
from image.loader import load_image
from core.performance import RenderCache


class Document:
    def __init__(self):
        self.image = None
        self.original_image = None  # Immutable source photo used for before/after.
        self.working_image = None   # Optional processed base, kept separate from source.
        self.path = None
        self.metadata = None
        self.adjustments = Adjustments()
        self.history = History()
        self.dirty = False
        self.render_cache = RenderCache(2)
        self.preview_cache = RenderCache(3)
        self._preview_source = None
        self._original_preview_source = None
        self._working_history = {}

    def _clear_caches(self):
        self._preview_source = None
        self._original_preview_source = None
        self.render_cache.clear()
        self.preview_cache.clear()

    def load(self, path):
        path = Path(path)
        image = load_image(path)
        self.original_image = image.copy()
        self.working_image = image.copy()
        self.image = self.working_image
        self.path = path
        self.metadata = None
        try:
            with Image.open(path) as source:
                exif = source.getexif()
                if exif:
                    self.metadata = exif.tobytes()
        except Exception:
            self.metadata = None
        self.adjustments.reset()
        self.history.clear()
        self._working_history.clear()
        self.history.push(self.adjustments)
        self._working_history[self.history._index] = self.working_image
        self._clear_caches()
        self.dirty = False

    def preview_source(self):
        source = self.working_image if self.working_image is not None else self.original_image
        if source is None:
            return None
        if self._preview_source is not None:
            return self._preview_source
        longest = max(source.size)
        if longest <= 1400:
            self._preview_source = source
        else:
            scale = 1400 / longest
            self._preview_source = source.resize(
                (max(1, int(source.width * scale)), max(1, int(source.height * scale))),
                Image.Resampling.BILINEAR,
            )
        return self._preview_source

    def original_preview_source(self):
        """Return a downscaled immutable source for the before/after comparison."""
        source = self.original_image
        if source is None:
            return None
        if self._original_preview_source is not None:
            return self._original_preview_source
        longest = max(source.size)
        if longest <= 1400:
            self._original_preview_source = source
        else:
            scale = 1400 / longest
            self._original_preview_source = source.resize(
                (max(1, int(source.width * scale)), max(1, int(source.height * scale))),
                Image.Resampling.BILINEAR,
            )
        return self._original_preview_source

    def render(self, preview=False):
        source_image = self.working_image if self.working_image is not None else self.original_image
        if source_image is None:
            return None
        cache = self.preview_cache if preview else self.render_cache
        key = (preview, id(source_image), repr(self.adjustments.to_dict()))
        cached = cache.get(key)
        if cached is not None:
            return cached
        source = self.preview_source() if preview else source_image
        result = render_image(source, self.adjustments)
        cache.put(key, result)
        return result

    def push_history(self):
        # History drops its oldest state when full; keep image snapshots aligned to it.
        states = self.history._states
        dropping_oldest = (
            self.history._index == len(states) - 1
            and len(states) >= self.history.maximum
        )
        self.history.push(self.adjustments)
        if dropping_oldest:
            self._working_history = {
                index - 1: image
                for index, image in self._working_history.items()
                if index > 0
            }
        self._working_history[self.history._index] = self.working_image
        valid = set(range(max(0, self.history._index - self.history.maximum + 1), self.history._index + 1))
        self._working_history = {i: image for i, image in self._working_history.items() if i in valid}
        self.render_cache.clear()
        self.preview_cache.clear()
        self._preview_source = None
        self.dirty = True

    def set_working_image(self, image):
        """Add a processed base as an undoable step without overwriting the source photo."""
        if self.original_image is None:
            raise ValueError("No image is open.")
        self.push_history()
        self.working_image = image.convert("RGB").copy()
        self.image = self.working_image
        self._working_history[self.history._index] = self.working_image
        self._clear_caches()
        self.dirty = True

    def set_adjustment(self, name, value, add_history=True):
        if not hasattr(self.adjustments, name):
            raise AttributeError(f"Unknown adjustment: {name}")
        setattr(self.adjustments, name, float(value))
        self.render_cache.clear()
        self.preview_cache.clear()
        self._preview_source = None
        self.dirty = True
        if add_history:
            self.push_history()

    def undo(self):
        state = self.history.undo()
        if state is None:
            return False
        self.adjustments = state
        self.working_image = self._working_history.get(self.history._index, self.original_image)
        self.image = self.working_image
        self._clear_caches()
        self.dirty = True
        return True

    def redo(self):
        state = self.history.redo()
        if state is None:
            return False
        self.adjustments = state
        self.working_image = self._working_history.get(self.history._index, self.original_image)
        self.image = self.working_image
        self._clear_caches()
        self.dirty = True
        return True

    def reset_adjustments(self):
        self.adjustments.reset()
        self._clear_caches()
        self.push_history()

    def has_image(self):
        return self.original_image is not None
