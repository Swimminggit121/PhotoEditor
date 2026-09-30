from pathlib import Path
from PIL import Image
from image.raw import raw_metadata
from image.loader import is_raw

def read_metadata(path):
    path=Path(path)
    result={"path":str(path),"filename":path.name,"extension":path.suffix.lower()}
    if is_raw(path):
        result.update(raw_metadata(path))
        return result
    with Image.open(path) as image:
        result.update({"format":image.format,"width":image.width,"height":image.height,"mode":image.mode})
        try:
            exif=image.getexif()
            result["exif"]={str(k):str(v) for k,v in exif.items()}
        except Exception:
            result["exif"]={}
    return result
