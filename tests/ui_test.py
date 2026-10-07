import os
import sys
import tempfile
from pathlib import Path
import time
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox, QPushButton

from app.window import MainWindow
from ui.batch_editor_dialog import BatchEditorDialog
from ui.canvas import ImageCanvas
from ui.help_dialog import HELP_TOPICS, HelpDialog
from ui.histogram import HistogramWidget
from ui.social_publish_dialog import SocialPublishDialog
from ui.video_editor_window import VideoEditorWindow
from ui.video_montage_dialog import VideoMontageDialog
from ui.video_montage_dialog import DuplicateReviewDialog
from processing.photo_duplicates import PhotoDuplicateGroup
from ui.workspace_launcher import WorkspaceLauncher
from core.photo_catalog import PhotoCatalog
from ui.photo_catalog_window import PhotoCatalogWindow
from ui.export_dialog import ExportDialog
from processing.video_render import VIDEO_EXPORT_PROFILES


def main():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    batch = BatchEditorDialog(window)
    batch.show()
    app.processEvents()

    upload_button = next(
        button for button in batch.findChildren(QPushButton)
        if button.text() == "Choose Photos Folder..."
    )
    assert upload_button.isVisible()
    assert upload_button.width() > 0 and upload_button.height() > 0
    assert batch.output_edit.isReadOnly()

    source = Image.new("RGB", (80, 60), (30, 40, 50))
    canvas = ImageCanvas()
    canvas.resize(480, 360)
    canvas.set_image(source.copy(), source)
    canvas.zoom = 2.0
    canvas.set_image(Image.new("RGB", source.size, (80, 90, 100)), source)
    assert canvas.zoom == 2.0

    histogram = HistogramWidget()
    histogram.resize(320, 180)
    histogram.set_image(source)
    histogram.show()
    app.processEvents()

    help_page = HelpDialog(window)
    assert help_page.topics.count() == len(HELP_TOPICS)
    help_page.search.setText("white balance")
    app.processEvents()
    assert help_page.topics.count() > 0
    assert any(
        "white balance" in HELP_TOPICS[help_page.topics.item(row).text()].casefold()
        for row in range(help_page.topics.count())
    )

    launcher = WorkspaceLauncher(allowed_modes={"video"})
    assert not launcher.video_action.isHidden()
    assert launcher.photo_action.isHidden()
    assert launcher.catalog_action.isHidden()
    full_launcher = WorkspaceLauncher(allowed_modes={"photo", "video"})
    assert not full_launcher.catalog_action.isHidden()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        shoot = root / "catalog-shoot"
        shoot.mkdir()
        photo_path = shoot / "catalog-photo.png"
        Image.new("RGB", (64, 48), (70, 120, 190)).save(photo_path)
        catalog = PhotoCatalog(root / "catalog.sqlite3")
        shoot_id = catalog.add_shoot(shoot)
        catalog.index_shoot(shoot_id)
        photo = catalog.photos(shoot_id)[0]
        catalog.update_photo(photo.id, rating=4, status="pick", keywords="portraits, studio")
        catalog_window = PhotoCatalogWindow(catalog=catalog)
        catalog_window.resize(1050, 650)
        catalog_window.show()
        app.processEvents()
        assert catalog_window.detail_scroll.widget() is not None
        assert catalog_window.preview.height() == 360
        assert catalog_window.table.rowCount() == 1
        assert catalog_window.table.columnCount() == 7
        opened_from_double_click = []
        catalog_window.photo_selected.connect(opened_from_double_click.append)
        catalog_window.table.selectRow(0)
        catalog_window.table.cellDoubleClicked.emit(0, 2)
        assert opened_from_double_click == [str(photo_path.resolve())]
        preview_deadline = time.monotonic() + 10
        while catalog_window._preview_workers and time.monotonic() < preview_deadline:
            app.processEvents()
            time.sleep(0.01)
        assert not catalog_window._preview_pixmap.isNull()
        catalog_window.search.setText("studio")
        app.processEvents()
        assert catalog_window.table.rowCount() == 1
        catalog_window.status_filter.setCurrentIndex(
            catalog_window.status_filter.findData("reject")
        )
        app.processEvents()
        assert catalog_window.table.rowCount() == 0
        catalog_window.status_filter.setCurrentIndex(
            catalog_window.status_filter.findData("pick")
        )
        app.processEvents()
        assert catalog_window.table.rowCount() == 1
        assert catalog_window.workspace_button.isEnabled()
        catalog_window.close()
    video_window = VideoEditorWindow()
    assert video_window.timeline.columnCount() == len(video_window.COLUMN_LABELS)
    assert video_window.export_profile.count() == len(VIDEO_EXPORT_PROFILES)
    video_window.export_profile.setCurrentIndex(2)
    assert video_window.export_profile.currentData() == "prores-422-hq"
    video_window.export_profile.setCurrentIndex(0)
    with tempfile.TemporaryDirectory() as temporary:
        frame_path = Path(temporary) / "timeline-frame.png"
        Image.new("RGB", (32, 24)).save(frame_path)
        clip = video_window.project.add_media(frame_path)
        video_window._refresh_table(clip.clip_id)
        assert [video_window.timeline.item(0, column).text() for column in range(9)] == [
            "0", "0.000", "0.000", "5.000", "100", "100", "0.000", "0.000", "IMAGE · timeline-frame.png",
        ]
        video_window.project.remove(clip.clip_id)
    video_window._refresh_table()
    publish_dialog = SocialPublishDialog()
    assert publish_dialog.platform.count() == 3
    assert not publish_dialog.publish.isEnabled()
    montage_dialog = VideoMontageDialog(window)
    assert montage_dialog.aspect_ratio.currentText() == "9:16"
    assert montage_dialog.template.count() == 4
    assert montage_dialog.duration.text() == "2.6"
    assert montage_dialog.use_current_edit.isEnabled() is False
    assert montage_dialog.auto_edit.isHidden()
    export_settings = ExportDialog(batch_mode=True)
    assert export_settings.recipe.currentText() == "Web JPEG · 2048 px"
    assert not export_settings.include_metadata.isChecked()
    assert export_settings.embed_srgb.isChecked()
    assert not export_settings.auto_edit.isChecked()
    assert export_settings.current_recipe().max_dimension == 2048
    master_index = export_settings.recipe.findText("16-bit TIFF · high-depth master")
    assert master_index >= 0
    export_settings.recipe.setCurrentIndex(master_index)
    master_recipe = export_settings.current_recipe()
    assert master_recipe.bit_depth == 16 and master_recipe.extension == ".tif"
    assert not export_settings.include_metadata.isEnabled()
    assert not export_settings.format.isEnabled()
    assert not export_settings.master_hint.isHidden()
    suite_montage_dialog = VideoMontageDialog(window, suite_mode=True)
    assert not suite_montage_dialog.auto_edit.isHidden()
    with tempfile.TemporaryDirectory() as temporary:
        selected_photo = Path(temporary) / "selected.png"
        Image.new("RGB", (24, 16), (130, 110, 90)).save(selected_photo)
        prefilled_montage = VideoMontageDialog(window, initial_paths=[selected_photo])
        assert prefilled_montage.photo_list.count() == 1
        assert Path(prefilled_montage.photo_list.item(0).text()) == selected_photo.resolve()
        prefilled_montage.close()
    duplicate_review = DuplicateReviewDialog([
        PhotoDuplicateGroup((Path("first.png"), Path("copy.jpg")), 93.8)
    ])
    assert not duplicate_review.buttons.button(QDialogButtonBox.Ok).isEnabled()
    duplicate_review.decisions[0].setCurrentIndex(duplicate_review.decisions[0].findData("all"))
    assert duplicate_review.buttons.button(QDialogButtonBox.Ok).isEnabled()
    assert duplicate_review.chosen_paths() == [Path("first.png"), Path("copy.jpg")]
    duplicate_review.decisions[0].setCurrentIndex(duplicate_review.decisions[0].findData("first"))
    assert duplicate_review.chosen_paths() == [Path("first.png")]
    window.document.dirty = True
    with patch("app.window.QMessageBox.warning", return_value=QMessageBox.Cancel):
        assert window._confirm_replace_document() is False
    with patch("app.window.QMessageBox.warning", return_value=QMessageBox.Discard):
        assert window._confirm_replace_document() is True
    window.document.dirty = False

    window.document.original_image = Image.new("RGB", (480, 320), (40, 60, 80))
    montage_with_edit = VideoMontageDialog(window)
    assert montage_with_edit.use_current_edit.isEnabled()
    window.document.history.push(window.document.adjustments)
    window.refresh_view()
    wait_until = time.monotonic() + 10
    while window.canvas.image is None and time.monotonic() < wait_until:
        app.processEvents()
        time.sleep(0.01)
    assert window.canvas.image is not None
    window.view_full_resolution()
    wait_until = time.monotonic() + 10
    while "100% source pixels" not in window.status_label.text() and time.monotonic() < wait_until:
        app.processEvents()
        time.sleep(0.01)
    assert window.canvas.image.size == (480, 320)
    assert "100% source pixels" in window.status_label.text()
    initial_exposure = window.document.adjustments.exposure
    window.change_adjustment("exposure", initial_exposure + 10)
    window.undo()
    assert window.document.adjustments.exposure == initial_exposure

    help_page.close()
    publish_dialog.close()
    montage_dialog.close()
    suite_montage_dialog.close()
    export_settings.close()
    duplicate_review.close()
    montage_with_edit.close()
    video_window.close()
    launcher.close()
    full_launcher.close()
    histogram.close()
    batch.close()
    window.document.dirty = False
    window.close()
    print("PhotoEditor UI test OK")


if __name__ == "__main__":
    main()
