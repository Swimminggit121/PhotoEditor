from dataclasses import dataclass,field,asdict

def create_hsl():
    return {c:{"hue":0.0,"saturation":0.0,"luminance":0.0} for c in ("red","orange","yellow","green","aqua","blue","purple","magenta")}
def create_grade(): return {"hue":0.0,"saturation":0.0,"luminance":0.0}

@dataclass
class Adjustments:
    exposure:float=0.0; contrast:float=0.0; highlights:float=0.0; shadows:float=0.0; whites:float=0.0; blacks:float=0.0
    temperature:float=0.0; tint:float=0.0; saturation:float=0.0; vibrance:float=0.0
    texture:float=0.0; clarity:float=0.0; dehaze:float=0.0; sharpening:float=0.0; noise_reduction:float=0.0; grain:float=0.0; vignette:float=0.0
    hsl:dict=field(default_factory=create_hsl)
    curves_master:list=field(default_factory=lambda:[(0.,0.),(1.,1.)])
    curves_red:list=field(default_factory=lambda:[(0.,0.),(1.,1.)])
    curves_green:list=field(default_factory=lambda:[(0.,0.),(1.,1.)])
    curves_blue:list=field(default_factory=lambda:[(0.,0.),(1.,1.)])
    grading_shadows:dict=field(default_factory=create_grade); grading_midtones:dict=field(default_factory=create_grade)
    grading_highlights:dict=field(default_factory=create_grade); grading_global:dict=field(default_factory=create_grade)
    grading_blending:float=50.0; grading_balance:float=0.0
    def copy(self): return Adjustments.from_dict(self.to_dict())
    def reset(self): self.__dict__.update(Adjustments().__dict__)
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls,data): return cls(**{k:v for k,v in data.items() if k in cls.__dataclass_fields__})
Adjustments=Adjustments
