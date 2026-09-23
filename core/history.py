from copy import deepcopy


class History:
    def __init__(self, maximum=100):
        self.maximum = maximum
        self._states = []
        self._index = -1

    def clear(self):
        self._states.clear()
        self._index = -1

    def push(self, state):
        if self._index < len(self._states) - 1:
            self._states = self._states[: self._index + 1]

        self._states.append(deepcopy(state))

        if len(self._states) > self.maximum:
            self._states.pop(0)

        self._index = len(self._states) - 1

    def undo(self):
        if not self.can_undo():
            return None

        self._index -= 1
        return deepcopy(self._states[self._index])

    def redo(self):
        if not self.can_redo():
            return None

        self._index += 1
        return deepcopy(self._states[self._index])

    def can_undo(self):
        return self._index > 0

    def can_redo(self):
        return self._index < len(self._states) - 1

    @property
    def current(self):
        if self._index < 0:
            return None

        return deepcopy(self._states[self._index])