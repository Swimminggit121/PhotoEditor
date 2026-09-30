from pathlib import Path
from PIL import Image,ExifTags
def read_metadata(path):
    result={}
    try:
        with Image.open(path) as im:
            exif=im.getexif()
            for tag,value in exif.items():result[ExifTags.TAGS.get(tag,str(tag))]=value
            result["width"]=im.width;result["height"]=im.height;result["format"]=im.format
    except Exception:pass
    return result
