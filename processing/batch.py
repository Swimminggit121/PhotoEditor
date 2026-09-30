from pathlib import Path
from core.document import Document
from image.export import export_image
from core.auto_grade import auto_colour_grade
SUPPORTED={".jpg",".jpeg",".png",".tif",".tiff",".webp",".bmp"}
def process_folder(input_dir,output_dir,auto_grade=False,quality=95):
    src=Path(input_dir);dst=Path(output_dir);dst.mkdir(parents=True,exist_ok=True);results=[]
    for path in sorted(src.iterdir()):
        if path.suffix.lower() not in SUPPORTED:continue
        doc=Document();doc.load(path)
        if auto_grade:doc.adjustments=auto_colour_grade(doc.original_image,doc.adjustments)
        out=dst/(path.stem+"_edited"+path.suffix.lower());export_image(doc.render(),out,quality);results.append(out)
    return results
