import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from core.photo_intelligence import analyse_folder, create_contact_sheet, hamming_distance
from core.social_export import PROFILES, export_social_image


def main():
    root = Path("photo_intelligence_test_output")
    root.mkdir(exist_ok=True)
    source = root / "source"
    source.mkdir(exist_ok=True)

    for index, color in enumerate(((30, 40, 50), (120, 130, 140), (220, 210, 190))):
        Image.new("RGB", (320, 240), color).save(source / f"photo_{index}.jpg")

    analyses = analyse_folder(source, recursive=False)
    assert len(analyses) == 3
    assert all(0 <= item.quality_score <= 100 for item in analyses)
    assert all(0 <= item.focal_x <= 1 and 0 <= item.focal_y <= 1 for item in analyses)
    assert hamming_distance(__import__("numpy").zeros(64, dtype="uint8"), __import__("numpy").zeros(64, dtype="uint8")) == 0

    sheet = create_contact_sheet(analyses, root / "contact_sheet.jpg")
    assert sheet.exists()

    output = root / "social.jpg"
    export_social_image(
        Image.open(source / "photo_1.jpg"),
        output,
        PROFILES["vertical"],
        focal_point=(0.2, 0.75),
    )
    with Image.open(output) as image:
        assert image.size == (1080, 1920)

    import shutil
    shutil.rmtree(root, ignore_errors=True)
    print("PHOTO INTELLIGENCE TEST OK")


if __name__ == "__main__":
    main()
