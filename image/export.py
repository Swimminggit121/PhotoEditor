from pathlib import Path
from PIL import Image

def export_image(image,path,quality=95,metadata=None):
    path=Path(path); suffix=path.suffix.lower(); image=image.convert("RGB"); kwargs={}
    if suffix in {".jpg",".jpeg"}: kwargs.update(format="JPEG",quality=max(1,min(100,int(quality))),optimize=True)
    elif suffix==".png": kwargs.update(format="PNG",optimize=True)
    elif suffix in {".tif",".tiff"}: kwargs.update(format="TIFF",compression="tiff_deflate")
    elif suffix==".webp": kwargs.update(format="WEBP",quality=max(1,min(100,int(quality))),method=6)
    else: raise ValueError(f"Unsupported export format: {suffix}")
    if metadata: kwargs["exif"]=metadata
    image.save(path,**kwargs)
