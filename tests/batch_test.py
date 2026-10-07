import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from core.batch_processor import BatchProcessor


def test_batch_auto_edit(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()

    for index in range(3):
        image = Image.new("RGB", (64, 48), (80 + index * 20, 110, 150))
        image.save(source / f"photo_{index}.jpg")

    processor = BatchProcessor(source, output, mode="auto_edit")
    result = processor.run()

    assert not result.cancelled
    assert len(result.failed) == 0
    assert len(result.processed) == 3
    assert all(path.exists() for path in result.processed)


def test_batch_social_pack(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()

    for index in range(2):
        image = Image.new("RGB", (96, 64), (80 + index * 25, 110, 150))
        image.save(source / f"social_{index}.jpg")

    processor = BatchProcessor(
        source,
        output,
        mode="auto_edit",
        social_pack=True,
        create_slideshow=True,
        slideshow_seconds=0.5,
    )
    result = processor.run()

    assert not result.cancelled
    assert not result.failed
    assert len(result.processed) == 2
    assert len(result.social_exports) == 8
    assert result.slideshow is not None
    assert result.slideshow.exists()


def test_batch_cancel(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()

    Image.new("RGB", (32, 32), (100, 100, 100)).save(source / "photo.jpg")

    processor = BatchProcessor(source, output, mode="auto_edit")
    processor.cancel()
    result = processor.run()

    assert result.cancelled
    assert result.processed == []
