import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from core.batch_processor import BatchProcessor

def test_batch_auto_edit(tmp_path):
    source=tmp_path/"source";output=tmp_path/"output";source.mkdir()
    for index in range(3): Image.new("RGB",(64,48),(80+index*20,110,150)).save(source/f"photo_{index}.jpg")
    result=BatchProcessor(source,output,mode="auto_edit").run()
    assert not result.cancelled and len(result.failed)==0 and len(result.processed)==3
    assert all(path.exists() for path in result.processed)

def test_batch_social_pack(tmp_path):
    source=tmp_path/"source";output=tmp_path/"output";source.mkdir()
    for index in range(2): Image.new("RGB",(96,64),(80+index*25,110,150)).save(source/f"social_{index}.jpg")
    result=BatchProcessor(source,output,mode="auto_edit",social_pack=True,create_slideshow=True,slideshow_seconds=0.5).run()
    assert not result.cancelled and not result.failed and len(result.processed)==2
    assert len(result.social_exports)==8 and result.slideshow and result.slideshow.exists()

def test_batch_cancel(tmp_path):
    source=tmp_path/"source";output=tmp_path/"output";source.mkdir()
    Image.new("RGB",(32,32),(100,100,100)).save(source/"photo.jpg")
    processor=BatchProcessor(source,output,mode="auto_edit");processor.cancel();result=processor.run()
    assert result.cancelled and result.processed==[]
