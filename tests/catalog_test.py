import shutil
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

import numpy as np
from PIL import Image
from PIL import ExifTags
from PIL import ImageCms

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.batch_processor import BatchProcessor
from core.photo_catalog import PhotoCatalog, analyze_photo_quality, export_metadata
from image.export import EXPORT_RECIPES, export_with_recipe, srgb_profile_bytes
from image.loader import load_image


def make_gradient():
    y, x = np.mgrid[:96, :128]
    pixels = np.stack(
        (x * 2, y * 2, (x + y) // 2 + 45),
        axis=-1,
    ).clip(0, 255).astype(np.uint8)
    return Image.fromarray(pixels)


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        originals = root / "Spring Portraits"
        originals.mkdir()
        original = originals / "frame-001.png"
        encoded_copy = originals / "renamed-frame.jpg"
        unrelated = originals / "frame-002.png"
        dark = originals / "check-dark.png"
        make_gradient().save(original)
        make_gradient().save(encoded_copy, quality=94)
        Image.new("RGB", (128, 96), (20, 70, 220)).save(unrelated)
        Image.new("RGB", (128, 96), (0, 0, 0)).save(dark)

        metadata_image = Image.new("RGB", (96, 64), (90, 130, 170))
        exif = Image.Exif()
        exif[271] = "Example Camera Co"
        exif[272] = "Model 1"
        exif[ExifTags.IFD.Exif] = {
            36867: "2025:04:15 10:30:00",
            42036: "Portrait Prime 50mm",
        }
        metadata_image.save(original, exif=exif)
        before = original.read_bytes()

        database = root / "catalog.sqlite3"
        catalog = PhotoCatalog(database)
        shoot_id = catalog.add_shoot(originals)
        result = catalog.index_shoot(shoot_id)
        assert result.indexed == 4
        assert result.duplicate_groups == 0
        # The EXIF-bearing photo intentionally differs from the copy now saved over it.
        assert not result.errors
        records = catalog.photos(shoot_id)
        assert len(records) == 4
        assert len(catalog.photos(shoot_id, limit=2)) == 2
        assert len(catalog.photos(shoot_id, limit=2, offset=2)) == 2
        assert not catalog.photos(shoot_id, limit=2, offset=10)
        assert len(catalog.photos(shoot_id, sort="quality")) == 4
        assert len(catalog.photos(shoot_id, sort="warnings")) == 4
        try:
            catalog.photos(shoot_id, sort="unknown")
        except ValueError:
            pass
        else:
            raise AssertionError("Unsupported catalog sort order was accepted.")
        source_record = next(record for record in records if record.name == original.name)
        assert source_record.camera == "Example Camera Co Model 1"
        assert source_record.lens == "Portrait Prime 50mm"
        assert source_record.captured_at.startswith("2025-04-15 10:30:00")
        assert "possible soft focus" in next(record for record in records if record.name == dark.name).quality_notes

        catalog.update_photo(source_record.id, rating=5, status="pick", keywords="client, portraits, client")
        assert catalog.photos(shoot_id, query="PORTRAITS")[0].keywords == "client, portraits"
        assert catalog.photos(shoot_id, query="example camera")[0].id == source_record.id
        assert catalog.photos(shoot_id, query="frame-001.png")[0].id == source_record.id
        assert catalog.photos(shoot_id, status="pick")[0].rating == 5
        assert len(catalog.photos(shoot_id, issues_only=True)) >= 1

        report_image = Image.new("RGB", (160, 100), (0, 0, 0))
        score, notes = analyze_photo_quality(report_image)
        assert 0 <= score <= 100
        assert "possible soft focus" in notes and "large area of deep shadows" in notes

        duplicate_dir = root / "duplicate shoot"
        duplicate_dir.mkdir()
        make_gradient().save(duplicate_dir / "first.png")
        make_gradient().save(duplicate_dir / "copy.jpg", quality=94)
        duplicate_shoot = catalog.add_shoot(duplicate_dir)
        duplicate_result = catalog.index_shoot(duplicate_shoot)
        assert duplicate_result.duplicate_groups == 1
        duplicate_records = catalog.photos(duplicate_shoot)
        assert all(record.duplicate_group for record in duplicate_records)
        assert all(record.status == "unreviewed" for record in duplicate_records)

        backup = root / "catalog-backup.sqlite3"
        catalog.backup(backup)
        catalog.update_photo(source_record.id, rating=1, status="reject")
        catalog.restore(backup)
        restored = next(record for record in catalog.photos(shoot_id) if record.id == source_record.id)
        assert restored.rating == 5 and restored.status == "pick"

        new_root = root / "moved originals"
        shutil.copytree(originals, new_root)
        catalog.relink_shoot(shoot_id, new_root)
        relinked = next(record for record in catalog.photos(shoot_id) if record.name == original.name)
        assert relinked.path.parent == new_root.resolve() and not relinked.missing
        assert catalog.photos(shoot_id, query="frame-001.png")[0].path.parent == new_root.resolve()
        relink_result = catalog.index_shoot(shoot_id)
        assert relink_result.indexed == 4
        assert original.read_bytes() == before

        with closing(sqlite3.connect(database)) as connection:
            connection.execute("DROP TABLE photo_search")
            connection.execute("UPDATE catalog_meta SET value='1' WHERE key='version'")
            connection.commit()
        migrated_catalog = PhotoCatalog(database)
        assert migrated_catalog.photos(shoot_id, query="example camera")[0].id == source_record.id

        recipe = EXPORT_RECIPES[0]
        rendered = make_gradient().resize((3200, 2400))
        output = root / "exports" / "preview.jpg"
        first_path = export_with_recipe(rendered, output, recipe)
        second_path = export_with_recipe(rendered, output, recipe)
        with Image.open(first_path) as exported:
            assert exported.size == (2048, 1536)
            assert exported.info.get("icc_profile")
        assert first_path != second_path and second_path.exists()

        small_recipe = recipe.__class__(
            recipe.key, recipe.label, recipe.extension, recipe.quality, 100,
            include_metadata=False, embed_srgb=True,
        )
        small_path = export_with_recipe(rendered, root / "small.jpg", small_recipe)
        with Image.open(small_path) as exported:
            assert exported.size == (100, 75)
            assert not exported.getexif()

        batch_output = root / "batch-edited"
        batch = BatchProcessor(
            originals,
            batch_output,
            mode="original",
            recipe=small_recipe,
            input_files=[unrelated],
        )
        batch_result = batch.run()
        assert len(batch_result.processed) == 1 and not batch_result.failed
        assert batch_result.processed[0].parent == batch_output
        assert unrelated.exists()

        metadata_recipe = recipe.__class__(
            recipe.key, recipe.label, recipe.extension, recipe.quality, None,
            include_metadata=True, embed_srgb=True,
        )
        metadata_path = export_with_recipe(
            metadata_image, root / "with-metadata.jpg", metadata_recipe, export_metadata(original)
        )
        with Image.open(metadata_path) as exported:
            assert exported.getexif().get(271) == "Example Camera Co"
            exported_exif = exported.getexif()
            assert exported_exif.get_ifd(ExifTags.IFD.Exif).get(36867) == "2025:04:15 10:30:00"

        oriented = root / "orientation.jpg"
        orientation = Image.Exif()
        orientation[274] = 6
        Image.new("RGB", (120, 60), (80, 120, 170)).save(
            oriented, exif=orientation, icc_profile=srgb_profile_bytes()
        )
        with Image.open(oriented) as source:
            converted = load_image(oriented)
            assert converted.size == (60, 120)
            assert source.info.get("icc_profile")

        privacy_recipe = recipe.__class__(
            recipe.key, recipe.label, recipe.extension, recipe.quality, None,
            include_metadata=False, embed_srgb=True,
        )
        privacy_path = export_with_recipe(
            metadata_image, root / "privacy-default.jpg", privacy_recipe, export_metadata(original)
        )
        with Image.open(privacy_path) as exported:
            assert not exported.getexif()
            assert exported.info.get("icc_profile")

    print("PHOTO CATALOG TEST OK")


if __name__ == "__main__":
    main()
