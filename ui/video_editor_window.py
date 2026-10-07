from __future__ import annotations

import copy
import tempfile
from pathlib import Path

import cv2
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QThread, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from processing.video_project import TimelineClip, VideoProject
from processing.video_render import VIDEO_EXPORT_PROFILES, export_video
from processing.titles import render_title
from ui.audio_library_dialog import AudioLibraryDialog
from ui.video_montage_dialog import VideoMontageDialog


class _RenderWorker(QThread):
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, project: VideoProject, output: Path, parent=None, profile="h264"):
        super().__init__(parent)
        self.project = project
        self.output = output
        self.profile = profile

    def run(self):
        try:
            self.completed.emit(str(export_video(self.project, self.output, self.profile)))
        except Exception as exc:
            self.failed.emit(str(exc))


class VideoEditorWindow(QMainWindow):
    COLUMN_LABELS = [
        "Track", "Start (s)", "Source In (s)", "Length (s)", "Volume %",
        "Opacity %", "Fade In (s)", "Fade Out (s)", "Media",
    ]

    def __init__(self, parent=None, on_home=None, suite_mode=False):
        super().__init__(parent)
        self.suite_mode = suite_mode
        self.setWindowTitle("PhotoEditor — Video Editor")
        self.setMinimumSize(1000, 650)
        self.resize(1440, 900)
        self.project = VideoProject()
        self.project_path: Path | None = None
        self.dirty = False
        self._loading_table = False
        self._render_worker: _RenderWorker | None = None
        self._preview_dir = tempfile.TemporaryDirectory(prefix="photoeditor-preview-")
        self.last_export_path: Path | None = None

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)
        self.player.durationChanged.connect(self._player_duration_changed)
        self.player.positionChanged.connect(self._player_position_changed)

        self.source_preview = QLabel("Import photos, video, or audio to start editing.")
        self.source_preview.setAlignment(Qt.AlignCenter)
        self.source_preview.setMinimumSize(420, 240)
        self.source_preview.setStyleSheet("background: #101010; border: 1px solid #333;")
        self.preview_stack = QWidget()
        preview_layout = QVBoxLayout(self.preview_stack)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(self.source_preview)
        preview_layout.addWidget(self.video_widget)
        self.video_widget.hide()

        self.timeline = QTableWidget(0, len(self.COLUMN_LABELS))
        self.timeline.setHorizontalHeaderLabels(self.COLUMN_LABELS)
        self.timeline.setSelectionBehavior(QTableWidget.SelectRows)
        self.timeline.setSelectionMode(QTableWidget.SingleSelection)
        self.timeline.horizontalHeader().setStretchLastSection(True)
        self.timeline.itemSelectionChanged.connect(self._show_source_frame)
        self.timeline.itemChanged.connect(self._edit_clip)

        self.position = QSlider(Qt.Horizontal)
        self.position.setRange(0, 10000)
        self.position.valueChanged.connect(self._position_changed)
        self.time_label = QLabel("00:00.000 / 00:00.000")
        self.status_label = QLabel("Ready — import media, arrange clips by track, trim, then preview and export.")

        import_button = QPushButton("Add Photos / Video")
        photo_video_button = QPushButton("Create photo-sequence video…")
        photo_video_button.setToolTip(
            "Build a standalone video from a selection or folder of already-edited photos."
        )
        import_audio = QPushButton("Add Audio File")
        title_button = QPushButton("Add Title")
        library_button = QPushButton("Licensed Audio Library")
        save_button = QPushButton("Save Project")
        open_button = QPushButton("Open Project")
        remove_button = QPushButton("Remove Clip")
        split_button = QPushButton("Split at Playhead")
        preview_button = QPushButton("Build Preview")
        export_button = QPushButton("Export Video…")
        publish_button = QPushButton("Publish reviewed video…")
        home_button = QPushButton("Photo / Video Hub")

        for button, handler in (
            (import_button, self.add_visual_media),
            (photo_video_button, self.create_photo_video),
            (import_audio, self.add_audio_file),
            (title_button, self.add_title),
            (library_button, self.open_audio_library),
            (save_button, self.save_project),
            (open_button, self.open_project),
            (remove_button, self.remove_selected),
            (split_button, self.split_selected),
            (preview_button, self.build_preview),
            (export_button, self.export_dialog),
            (publish_button, self.publish_dialog),
        ):
            button.clicked.connect(handler)
        if on_home:
            home_button.clicked.connect(on_home)
        else:
            home_button.setVisible(False)

        self.aspect = QComboBox()
        self.aspect.addItem("Landscape 16:9 · 1920×1080", (1920, 1080))
        self.aspect.addItem("Portrait 9:16 · 1080×1920", (1080, 1920))
        self.aspect.addItem("Square 1:1 · 1080×1080", (1080, 1080))
        self.aspect.addItem("Portrait 4:5 · 1080×1350", (1080, 1350))
        self.aspect.currentIndexChanged.connect(self._format_changed)
        self.export_profile = QComboBox()
        for profile in VIDEO_EXPORT_PROFILES:
            self.export_profile.addItem(profile.label, profile.key)
        self.export_profile.setToolTip(
            "Choose a web-compatible delivery, a 10-bit HEVC file, or an intraframe ProRes editing master."
        )
        self.frame_rate = QComboBox()
        self.frame_rate.addItems(["24", "25", "30", "50", "60"])
        self.frame_rate.setCurrentText(str(self.project.fps))
        self.frame_rate.currentTextChanged.connect(self._fps_changed)
        self.track_picker = QComboBox()
        self.track_picker.addItems(["V1 · Main", "V2 · Overlay", "A1 · Music / Sound"])
        self.track_picker.setCurrentIndex(0)

        actions = QHBoxLayout()
        for button in (
            open_button, save_button, import_button, import_audio, title_button, library_button,
        ):
            actions.addWidget(button)
        actions.addWidget(QLabel("Add to track"))
        actions.addWidget(self.track_picker)
        actions.addStretch(1)
        actions.addWidget(home_button)

        photo_sequence = QHBoxLayout()
        photo_sequence.addWidget(photo_video_button)
        photo_sequence.addWidget(QLabel(
            "Use finished photos, review visual duplicates, then choose a motion template and soundtrack."
        ))
        photo_sequence.addStretch(1)

        transport = QHBoxLayout()
        for button in (split_button, remove_button, preview_button, export_button, publish_button):
            transport.addWidget(button)
        transport.addStretch(1)
        transport.addWidget(QLabel("Sequence"))
        transport.addWidget(self.aspect)
        transport.addWidget(QLabel("FPS"))
        transport.addWidget(self.frame_rate)
        transport.addWidget(QLabel("Export"))
        transport.addWidget(self.export_profile)

        preview_controls = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_playback)
        preview_controls.addWidget(self.play_button)
        preview_controls.addWidget(self.position, 1)
        preview_controls.addWidget(self.time_label)

        inspector = QWidget()
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.addWidget(QLabel("TIMELINE — edit track, position, source trim, duration, and audio gain in place"))
        inspector_layout.addWidget(self.timeline, 1)
        inspector_layout.addWidget(QLabel(
            "V1 is the base picture; higher video tracks composite above it. A1 contains music and sound effects. "
            "Split at the playhead, move clips by editing Start, and trim the source with Source In and Length."
        ))
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.preview_stack)
        splitter.addWidget(inspector)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 3)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.addLayout(actions)
        root_layout.addLayout(photo_sequence)
        root_layout.addLayout(transport)
        root_layout.addWidget(splitter, 1)
        root_layout.addLayout(preview_controls)
        root_layout.addWidget(self.status_label)
        self.setCentralWidget(root)
        self._playback_timer = QTimer(self)
        self._playback_timer.setInterval(30)
        self._playback_timer.timeout.connect(self._advance_playhead)
        self._refresh_table()

    def _mark_dirty(self):
        self.dirty = True
        title = self.project.name + (" *" if self.dirty else "")
        self.setWindowTitle(f"PhotoEditor — Video Editor — {title}")
        if self.video_widget.isVisible():
            self.player.stop()
            self.video_widget.hide()
            self.source_preview.show()

    def add_visual_media(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add photos or video", "",
            "Media (*.jpg *.jpeg *.png *.tif *.tiff *.webp *.bmp *.mp4 *.mov *.mkv *.avi *.webm *.m4v *.mts *.m2ts)",
        )
        if not paths:
            return
        self._add_paths(paths)

    def create_photo_video(self):
        dialog = VideoMontageDialog(self, suite_mode=self.suite_mode)
        dialog.exec()

    def add_audio_file(self):
        self.track_picker.setCurrentIndex(2)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add audio files", "",
            "Audio (*.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus)",
        )
        if paths:
            self._add_paths(paths)

    def add_title(self):
        text, accepted = QInputDialog.getMultiLineText(self, "Add title clip", "Title text:")
        if not accepted or not text.strip():
            return
        try:
            clip = self.project.add_title(text, track=1, duration=4.0)
            self._mark_dirty()
            self._refresh_table(clip.clip_id)
        except Exception as exc:
            QMessageBox.critical(self, "Could not add title", str(exc))

    def _add_paths(self, paths):
        track = self.track_picker.currentIndex()
        added = []
        errors = []
        for path in paths:
            try:
                self.project.add_media(path, track=track)
                added.append(path)
            except Exception as exc:
                errors.append(f"{Path(path).name}: {exc}")
        if added:
            self._mark_dirty()
            self._refresh_table()
            self.status_label.setText(f"Added {len(added)} media file(s).")
        if errors:
            QMessageBox.critical(self, "Some media could not be added", "\n".join(errors))

    def open_audio_library(self):
        self.track_picker.setCurrentIndex(2)
        dialog = AudioLibraryDialog(self)
        dialog.audio_added.connect(lambda path: self._add_paths([path]))
        dialog.exec()

    def _refresh_table(self, select_id: str | None = None):
        ordered = sorted(self.project.clips, key=lambda clip: (clip.track, clip.start, clip.clip_id))
        self._loading_table = True
        self.timeline.blockSignals(True)
        self.timeline.setRowCount(len(ordered))
        for row, clip in enumerate(ordered):
            values = [
                str(clip.track),
                f"{clip.start:.3f}",
                f"{clip.source_in:.3f}",
                f"{clip.duration:.3f}",
                f"{clip.volume * 100:.0f}",
                f"{clip.opacity * 100:.0f}",
                f"{clip.fade_in:.3f}",
                f"{clip.fade_out:.3f}",
                f"TITLE · {clip.title[:48]}" if clip.kind == "title" else f"{clip.kind.upper()} · {Path(clip.path).name}",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, clip.clip_id)
                if column == 8:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.timeline.setItem(row, column, item)
            if clip.clip_id == select_id:
                self.timeline.selectRow(row)
        self.timeline.resizeColumnsToContents()
        self.timeline.blockSignals(False)
        self._loading_table = False
        self._update_timeline_controls()

    def _selected_clip(self) -> TimelineClip | None:
        row = self.timeline.currentRow()
        if row < 0:
            return None
        item = self.timeline.item(row, 0)
        if item is None:
            return None
        try:
            return self.project.clip(item.data(Qt.UserRole))
        except KeyError:
            return None

    def _edit_clip(self, item):
        if self._loading_table or item.column() not in {0, 1, 2, 3, 4, 5, 6, 7}:
            return
        clip = self._selected_clip()
        if clip is None:
            return
        clip_before = copy.copy(clip)
        try:
            value = float(item.text())
            if item.column() == 0:
                if not value.is_integer() or value < 0:
                    raise ValueError("Track number must be a non-negative integer.")
                clip_before.track = int(value)
            elif item.column() == 1:
                clip_before.start = value
            elif item.column() == 2:
                clip_before.source_in = value
            elif item.column() == 3:
                clip_before.duration = value
            elif item.column() == 4:
                clip_before.volume = value / 100
            elif item.column() == 5:
                clip_before.opacity = value / 100
            elif item.column() == 6:
                clip_before.fade_in = value
            elif item.column() == 7:
                clip_before.fade_out = value
            if (
                clip_before.start < 0 or clip_before.source_in < 0 or clip_before.duration <= 0
                or not 0 <= clip_before.volume <= 2 or not 0 <= clip_before.opacity <= 1
                or not 0 <= clip_before.fade_in <= clip_before.duration or not 0 <= clip_before.fade_out <= clip_before.duration
            ):
                raise ValueError("Use non-negative times, a positive length, volume 0–200%, opacity 0–100%, and fades no longer than the clip.")
            clip.track = clip_before.track
            clip.start = clip_before.start
            clip.source_in = clip_before.source_in
            clip.duration = clip_before.duration
            clip.volume = clip_before.volume
            clip.opacity = clip_before.opacity
            clip.fade_in = clip_before.fade_in
            clip.fade_out = clip_before.fade_out
            self._mark_dirty()
            self._refresh_table(clip.clip_id)
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, "Invalid clip setting", str(exc))
            self._refresh_table(clip.clip_id)

    def remove_selected(self):
        clip = self._selected_clip()
        if clip is None:
            return
        self.project.remove(clip.clip_id)
        self._mark_dirty()
        self._refresh_table()
        self._show_source_frame()

    def split_selected(self):
        clip = self._selected_clip()
        position = self._current_position()
        if clip is None or not (clip.start < position < clip.end):
            QMessageBox.information(self, "Split clip", "Move the playhead inside the selected clip first.")
            return
        original_end = clip.end
        original_source_in = clip.source_in
        clip.duration = position - clip.start
        second = TimelineClip(
            path=clip.path,
            kind=clip.kind,
            start=position,
            duration=original_end - position,
            source_in=original_source_in + clip.duration,
            track=clip.track,
            volume=clip.volume,
            include_source_audio=clip.include_source_audio,
            title=clip.title,
        )
        self.project.clips.append(second)
        self._mark_dirty()
        self._refresh_table(second.clip_id)

    def _format_changed(self, index):
        self.project.width, self.project.height = self.aspect.itemData(index)
        self._mark_dirty()

    def _fps_changed(self, value):
        try:
            self.project.fps = int(value)
            self._mark_dirty()
        except ValueError:
            return

    def _current_position(self) -> float:
        return self.project.duration * self.position.value() / 10000 if self.project.duration else 0.0

    def _position_changed(self, value):
        if self.player.source().isValid() and self.video_widget.isVisible():
            duration_ms = self.player.duration()
            if duration_ms:
                self.player.setPosition(int(duration_ms * value / 10000))
        else:
            self._show_source_frame()
        self._update_time_label()

    def _update_timeline_controls(self):
        self.position.setEnabled(bool(self.project.clips))
        self._update_time_label()

    def _update_time_label(self):
        current = self._current_position()
        total = self.project.duration
        self.time_label.setText(f"{self._fmt_time(current)} / {self._fmt_time(total)}")

    @staticmethod
    def _fmt_time(value: float) -> str:
        minutes, seconds = divmod(max(0, value), 60)
        return f"{int(minutes):02}:{seconds:06.3f}"

    def _show_source_frame(self):
        if self.video_widget.isVisible():
            return
        position = self._current_position()
        candidates = [clip for clip in self.project.clips if clip.kind in {"image", "video", "title"} and clip.start <= position < clip.end]
        clip = max(candidates, key=lambda item: (item.track, item.start), default=None)
        if clip is None:
            self.source_preview.setText("No picture clip at the playhead.")
            self.source_preview.setPixmap(QPixmap())
            return
        try:
            if clip.kind == "title":
                pixmap = QPixmap.fromImage(ImageQt(render_title(clip.title, self.project.width, self.project.height)))
            elif clip.kind == "image":
                with Image.open(clip.path) as image:
                    frame = image.convert("RGB")
                    pixmap = QPixmap.fromImage(ImageQt(frame))
            else:
                capture = cv2.VideoCapture(clip.path)
                try:
                    capture.set(cv2.CAP_PROP_POS_MSEC, (clip.source_in + position - clip.start) * 1000)
                    ok, frame_array = capture.read()
                finally:
                    capture.release()
                if not ok:
                    self.source_preview.setText("Could not decode this video frame.")
                    return
                frame = Image.fromarray(cv2.cvtColor(frame_array, cv2.COLOR_BGR2RGB))
                pixmap = QPixmap.fromImage(ImageQt(frame))
            self.source_preview.setPixmap(pixmap.scaled(self.source_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.source_preview.setToolTip(f"{Path(clip.path).name} · source preview")
        except Exception as exc:
            self.source_preview.setText(f"Preview unavailable: {exc}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.video_widget.isVisible():
            self._show_source_frame()

    def build_preview(self):
        if not self.project.clips:
            QMessageBox.information(self, "Build Preview", "Add media to the timeline first.")
            return
        if self._render_worker and self._render_worker.isRunning():
            return
        project = copy.deepcopy(self.project)
        scale = min(1.0, 960 / project.width, 960 / project.height)
        project.width = max(2, int(project.width * scale) // 2 * 2)
        project.height = max(2, int(project.height * scale) // 2 * 2)
        output = Path(self._preview_dir.name) / "sequence-preview.mp4"
        self._render_worker = _RenderWorker(project, output, self)
        self._render_worker.completed.connect(self._preview_ready)
        self._render_worker.failed.connect(self._render_failed)
        self._render_worker.finished.connect(lambda: self._set_rendering(False))
        self._set_rendering(True)
        self._render_worker.start()

    def export_dialog(self):
        if not self.project.clips:
            QMessageBox.information(self, "Export Video", "Add media to the timeline first.")
            return
        if self._render_worker and self._render_worker.isRunning():
            return
        profile = self.export_profile.currentData()
        profile_definition = next(item for item in VIDEO_EXPORT_PROFILES if item.key == profile)
        default = str(
            (self.project_path.parent if self.project_path else Path.home())
            / f"edited-video{profile_definition.extension}"
        )
        file_filter = f"{profile_definition.label} (*{profile_definition.extension})"
        output, _ = QFileDialog.getSaveFileName(
            self, "Export video", default, file_filter
        )
        if not output:
            return
        if Path(output).suffix.casefold() != profile_definition.extension:
            output = str(Path(output).with_suffix(profile_definition.extension))
        self._render_worker = _RenderWorker(
            copy.deepcopy(self.project), Path(output), parent=self, profile=profile
        )
        self._render_worker.completed.connect(self._export_ready)
        self._render_worker.failed.connect(self._render_failed)
        self._render_worker.finished.connect(lambda: self._set_rendering(False))
        self._set_rendering(True)
        self._render_worker.start()

    def _set_rendering(self, rendering):
        self.status_label.setText("Rendering — this may take a while…" if rendering else "Ready.")
        for button in self.findChildren(QPushButton):
            if button.text() in {"Build Preview", "Export Video…"}:
                button.setEnabled(not rendering)

    def _render_failed(self, message):
        QMessageBox.critical(self, "Video render failed", message)
        self.status_label.setText("Render failed — review the message and try again.")

    def _preview_ready(self, path):
        self.player.stop()
        self.video_widget.show()
        self.source_preview.hide()
        self.player.setSource(QUrl.fromLocalFile(path))
        self.status_label.setText("Preview rendered. Play and watch the sequence before export or publishing.")

    def _export_ready(self, path):
        self.last_export_path = Path(path)
        self.status_label.setText(f"Exported: {Path(path).name}")
        QMessageBox.information(self, "Export complete", f"Video saved to:\n{path}")

    def publish_dialog(self):
        from ui.social_publish_dialog import SocialPublishDialog

        dialog = SocialPublishDialog(self, self.last_export_path)
        dialog.exec()

    def toggle_playback(self):
        if self.video_widget.isVisible() and self.player.source().isValid():
            if self.player.playbackState() == QMediaPlayer.PlayingState:
                self.player.pause()
                self.play_button.setText("Play")
            else:
                self.player.play()
                self.play_button.setText("Pause")
            return
        self._playback_timer.start()
        self.play_button.setText("Pause")

    def _advance_playhead(self):
        if not self.project.duration:
            self._playback_timer.stop()
            return
        next_position = self._current_position() + self._playback_timer.interval() / 1000
        if next_position >= self.project.duration:
            self._playback_timer.stop()
            self.play_button.setText("Play")
            next_position = 0
        self.position.setValue(round(next_position / self.project.duration * 10000))

    def _player_duration_changed(self, _duration):
        self._update_time_label()

    def _player_position_changed(self, position):
        duration = self.player.duration()
        if duration and self.video_widget.isVisible():
            self.position.blockSignals(True)
            self.position.setValue(round(position / duration * 10000))
            self.position.blockSignals(False)
            self.time_label.setText(f"{self._fmt_time(position / 1000)} / {self._fmt_time(duration / 1000)}")

    def save_project(self):
        default = str(self.project_path or (Path.home() / "Untitled.videoedit"))
        path, _ = QFileDialog.getSaveFileName(self, "Save video project", default, "Video project (*.videoedit)")
        if not path:
            return
        if Path(path).suffix.casefold() != ".videoedit":
            path += ".videoedit"
        try:
            self.project.save(path)
            self.project_path = Path(path)
            self.project.name = self.project_path.stem
            self.dirty = False
            self._mark_saved()
            self.status_label.setText(f"Project saved: {self.project_path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Could not save project", str(exc))

    def _mark_saved(self):
        self.setWindowTitle(f"PhotoEditor — Video Editor — {self.project.name}")

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open video project", "", "Video project (*.videoedit)")
        if not path:
            return
        try:
            self.project = VideoProject.load(path)
            self.project_path = Path(path)
            self.dirty = False
            self.setWindowTitle(f"PhotoEditor — Video Editor — {self.project.name}")
            self.aspect.blockSignals(True)
            self.aspect.setCurrentIndex(next(
                (index for index in range(self.aspect.count()) if self.aspect.itemData(index) == (self.project.width, self.project.height)),
                0,
            ))
            self.aspect.blockSignals(False)
            self.frame_rate.blockSignals(True)
            self.frame_rate.setCurrentText(str(self.project.fps))
            self.frame_rate.blockSignals(False)
            self._refresh_table()
            self.status_label.setText(f"Project opened: {self.project_path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Could not open project", str(exc))

    def closeEvent(self, event):
        if self._render_worker and self._render_worker.isRunning():
            QMessageBox.information(
                self, "Video render in progress",
                "Wait for the current preview or export to finish before closing the editor.",
            )
            event.ignore()
            return
        if self.dirty:
            answer = QMessageBox.question(
                self, "Unsaved video project",
                "Discard unsaved timeline changes and close the video editor?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )
            if answer == QMessageBox.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.Save:
                self.save_project()
                if self.dirty:
                    event.ignore()
                    return
        self.player.stop()
        self.player.setSource(QUrl())
        self._preview_dir.cleanup()
        event.accept()
