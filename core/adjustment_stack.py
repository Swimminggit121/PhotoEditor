from dataclasses import dataclass, asdict


@dataclass
class Adjustments:
    exposure: float = 0.0
    contrast: float = 0.0

    highlights: float = 0.0
    shadows: float = 0.0

    whites: float = 0.0
    blacks: float = 0.0

    temperature: float = 0.0
    tint: float = 0.0

    saturation: float = 0.0
    vibrance: float = 0.0

    def copy(self):
        return Adjustments(**asdict(self))

    def reset(self):
        self.exposure = 0.0
        self.contrast = 0.0
        self.highlights = 0.0
        self.shadows = 0.0
        self.whites = 0.0
        self.blacks = 0.0
        self.temperature = 0.0
        self.tint = 0.0
        self.saturation = 0.0
        self.vibrance = 0.0

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)