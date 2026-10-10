from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.document import Document
from core.project import load_project, save_project
from ai.masks import mask_to_local_adjustment
from masks.raster import rasterize_mask


def test_ai_mask_is_compact_and_rasterizes():
    source = np.zeros((24, 32), dtype=np.uint8)
    source[:, :16] = 255
    adjustment = mask_to_local_adjustment(source, "Test AI Mask")
    assert "mask_png" in adjustment
    assert "mask" not in adjustment
    result = rasterize_mask(adjustment, (24, 32))
    assert result.shape == (24, 32)
    assert float(result[:, :12].mean()) > 0.95
    assert float(result[:, 20:].mean()) < 0.05


def test_enhancement_preserves_source_and_supports_undo_redo():
    document = Document()
    original = Image.new("RGB", (20, 16), (10, 20, 30))
    enhanced = Image.new("RGB", (40, 32), (200, 150, 100))
    document.original_image = original.copy()
    document.working_image = original.copy()
    document.image = document.working_image
    document.history.clear()
    document._working_history.clear()
    document.history.push(document.adjustments)
    document._working_history[document.history._index] = document.working_image

    document.set_working_image(enhanced)
    assert document.original_image.size == (20, 16)
    assert document.working_image.size == (40, 32)
    assert document.undo()
    assert document.working_image.size == (20, 16)
    assert document.redo()
    assert document.working_image.size == (40, 32)
    assert document.original_image.getpixel((0, 0)) == (10, 20, 30)


def test_project_round_trip_preserves_working_image_and_metadata():
    document = Document()
    document.original_image = Image.new("RGB", (18, 12), (20, 40, 60))
    document.working_image = Image.new("RGB", (36, 24), (180, 140, 100))
    document.image = document.working_image
    document.metadata = b"test-exif-payload"
    document.history.clear()
    document._working_history.clear()
    document.history.push(document.adjustments)
    document._working_history[document.history._index] = document.working_image

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "roundtrip.photoedit"
        save_project(document, path)
        loaded = Document()
        load_project(loaded, path)
        assert loaded.original_image.size == (18, 12)
        assert loaded.working_image.size == (36, 24)
        assert loaded.working_image.getpixel((0, 0)) == (180, 140, 100)
        assert loaded.metadata == b"test-exif-payload"
        assert loaded.render(preview=True).size == (36, 24)


if __name__ == "__main__":
    test_ai_mask_is_compact_and_rasterizes()
    test_enhancement_preserves_source_and_supports_undo_redo()
    test_project_round_trip_preserves_working_image_and_metadata()
    print("REGRESSION TESTS OK")
