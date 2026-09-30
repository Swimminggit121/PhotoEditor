from collections import OrderedDict


class RenderCache:
    def __init__(self, max_items=8):
        self.max_items = max(1, int(max_items))
        self._items = OrderedDict()

    def get(self, key):
        value = self._items.get(key)
        if value is not None:
            self._items.move_to_end(key)
        return value

    def put(self, key, value):
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self.max_items:
            self._items.popitem(last=False)

    def clear(self):
        self._items.clear()
