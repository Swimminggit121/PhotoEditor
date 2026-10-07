import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
import numpy as np
import tifffile

from core.batch_processor import BatchProcessor
from image.export import EXPORT_RECIPES


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


def test_recursive_batch_skips_its_output_folder(tmp_path):
    source = tmp_path / "source"
    output = source / "edited"
    nested = source / "trip"
    output.mkdir(parents=True)
    nested.mkdir()
    Image.new("RGB", (16, 16)).save(nested / "photo.jpg")
    Image.new("RGB", (16, 16)).save(output / "previous_export.jpg")

    processor = BatchProcessor(source, output, recursive=True)
    assert processor.files() == [nested / "photo.jpg"]


def test_batch_distinguishes_raw_and_raster_with_same_stem(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    jpeg = source / "photo.jpg"
    raw = source / "photo.cr2"
    jpeg.touch()
    raw.touch()

    processor = BatchProcessor(source, tmp_path / "output")
    destinations = processor._destinations([jpeg, raw])
    assert len({destination for _, destination in destinations}) == 2
    assert processor._input_profile(jpeg) == "jpeg"
    assert processor._input_profile(raw) == "raw"


def test_batch_rejects_output_equal_to_input(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    processor = BatchProcessor(source, source)
    try:
        processor.run()
    except ValueError as exc:
        assert "separate output folder" in str(exc)
    else:
        raise AssertionError("Batch export was allowed to target its input folder.")


def test_batch_preserves_16bit_tiff_master(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    pixels = np.zeros((20, 24, 3), dtype=np.uint16)
    pixels[..., 0] = np.arange(24, dtype=np.uint16) * 1000
    pixels[..., 1] = 14000
    pixels[..., 2] = 31000
    tifffile.imwrite(source / "master.tif", pixels, photometric="rgb")

    recipe = next(recipe for recipe in EXPORT_RECIPES if recipe.bit_depth == 16)
    result = BatchProcessor(source, output, mode="original", recipe=recipe).run()
    assert not result.failed
    exported = tifffile.imread(result.processed[0])
    assert exported.dtype == np.uint16
    assert np.array_equal(exported, pixels)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "success"
        root.mkdir()
        test_batch_auto_edit(root)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "cancel"
        root.mkdir()
        test_batch_cancel(root)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "master"
        root.mkdir()
        test_batch_preserves_16bit_tiff_master(root)
    print("BATCH TESTS OK")
