from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, QUrl, Qt, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
)

from social import publishing


PLATFORMS = {
    "YouTube": "youtube",
    "Instagram Reel": "instagram",
    "Facebook Page Reel": "facebook",
}


class _SocialWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.action = action

    def run(self):
        try:
            self.succeeded.emit(self.action())
        except Exception as exc:
            self.failed.emit(str(exc))


class SocialPublishDialog(QDialog):
    def __init__(self, parent=None, video_path: str | Path | None = None):
        super().__init__(parent)
        self.setWindowTitle("Review and Publish Video")
        self.resize(900, 780)
        self._worker: _SocialWorker | None = None
        self._duration_ms = 0
        self._last_position = -1
        self._watched_bins = set()
        self._finished = False
        self._published_url = ""

        self.platform = QComboBox()
        self.platform.addItems(PLATFORMS)
        self.connect_button = QPushButton("Connect account…")
        self.settings_button = QPushButton("Publish Settings…")
        self.account = QComboBox()

        self.video_path = QLineEdit(str(video_path or ""))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_video)
        video_row = QHBoxLayout()
        video_row.addWidget(self.video_path, 1)
        video_row.addWidget(browse)
        self.title = QLineEdit()
        self.description = QPlainTextEdit()
        self.description.setPlaceholderText("Caption / description")
        self.description.setMaximumHeight(90)
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("Comma-separated YouTube tags")
        self.privacy = QComboBox()
        self.privacy.addItems(["Private", "Unlisted", "Public"])
        self.public_url = QLineEdit()
        self.public_url.setPlaceholderText("Public HTTPS URL that serves this exact MP4")
        self.public_url.setToolTip(
            "Instagram's API fetches the video from your public server. Configure your own approved hosting; "
            "PhotoEditor does not upload your file to a third-party storage service."
        )

        form = QFormLayout()
        form.addRow("Platform", self.platform)
        form.addRow("Account / Page", self.account)
        form.addRow("", self.connect_button)
        form.addRow("Final MP4", video_row)
        form.addRow("Title", self.title)
        form.addRow("Caption / description", self.description)
        form.addRow("YouTube tags", self.tags)
        form.addRow("YouTube privacy", self.privacy)
        form.addRow("Instagram hosted URL", self.public_url)

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(250)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.durationChanged.connect(self._duration_changed)
        self.player.positionChanged.connect(self._position_changed)
        self.player.mediaStatusChanged.connect(self._media_status_changed)
        self.player.errorOccurred.connect(
            lambda _error, message: self.result.setText(f"Playback error: {message}")
        )
        self.review = QCheckBox("I watched the complete export, reviewed this post, and approve publishing it.")
        self.review.setEnabled(False)
        self.review.stateChanged.connect(self._update_publish_enabled)
        self.play = QPushButton("Play final export")
        self.play.clicked.connect(self._play_video)
        self.review_progress = QProgressBar()
        self.review_progress.setRange(0, 100)
        self.review_progress.setValue(0)
        self.publish = QPushButton("Publish now")
        self.publish.setEnabled(False)
        self.publish.clicked.connect(self._publish)
        self.settings_button.clicked.connect(self._open_settings)
        self.connect_button.clicked.connect(self._connect)
        self.platform.currentTextChanged.connect(self._platform_changed)
        self.title.textChanged.connect(self._post_changed)
        self.description.textChanged.connect(self._post_changed)
        self.tags.textChanged.connect(self._post_changed)
        self.privacy.currentTextChanged.connect(self._post_changed)
        self.public_url.textChanged.connect(self._post_changed)
        self.video_path.textChanged.connect(self._video_path_changed)
        self.account.currentIndexChanged.connect(self._post_changed)

        self.result = QLabel(
            "Publishing uses the platform’s official APIs. YouTube defaults to Private. "
            "Instagram publishing requires a professional account and a public HTTPS media URL."
        )
        self.result.setWordWrap(True)
        buttons = QHBoxLayout()
        buttons.addWidget(self.play)
        buttons.addStretch(1)
        buttons.addWidget(self.settings_button)
        buttons.addWidget(self.publish)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("Watch the final export before you approve publishing"))
        layout.addWidget(self.video_widget, 1)
        review_row = QHBoxLayout()
        review_row.addWidget(self.review_progress, 1)
        review_row.addWidget(self.review)
        layout.addLayout(review_row)
        layout.addWidget(self.result)
        layout.addLayout(buttons)
        self._refresh_accounts()
        self._platform_changed()
        if video_path:
            self._load_video(str(video_path))

    def _platform_key(self):
        return PLATFORMS[self.platform.currentText()]

    def _browse_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose final MP4", "", "MP4 video (*.mp4)")
        if path:
            self.video_path.setText(path)

    def _video_path_changed(self, path):
        self._load_video(path)
        self._update_publish_enabled()

    def _post_changed(self, *_args):
        self.review.setChecked(False)
        self._update_publish_enabled()

    def _load_video(self, path):
        file = Path(path).expanduser()
        self.player.stop()
        self._duration_ms = 0
        self.review.setChecked(False)
        self.review.setEnabled(False)
        self._watched_bins.clear()
        self.review_progress.setValue(0)
        self._finished = False
        self._last_position = -1
        if not file.is_file() or file.suffix.casefold() != ".mp4":
            self.player.stop()
            self.player.setSource(QUrl())
            self._update_publish_enabled()
            return
        self.player.setSource(QUrl.fromLocalFile(str(file.resolve())))

    def _duration_changed(self, duration):
        self._duration_ms = duration
        if duration > 0:
            self.title.setText(self.title.text() or Path(self.video_path.text()).stem)

    def _position_changed(self, position):
        if self.player.playbackState() == QMediaPlayer.PlayingState and self._last_position >= 0:
            delta = position - self._last_position
            if 0 < delta <= 750 and self._duration_ms > 0:
                first = max(0, int(self._last_position / self._duration_ms * 200))
                last = min(199, int(position / self._duration_ms * 200))
                self._watched_bins.update(range(first, last + 1))
                self.review_progress.setValue(min(100, round(len(self._watched_bins) / 200 * 100)))
                self._update_review_state()
        self._last_position = position

    def _media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self._finished = True
            self._update_review_state()

    def _update_review_state(self):
        fully_watched = self._finished and len(self._watched_bins) >= 190
        self.review.setEnabled(fully_watched)
        if fully_watched:
            self.result.setText("Full playback completed. Check the review approval box to enable the publish action.")
        self._update_publish_enabled()

    def _play_video(self):
        path = self.video_path.text().strip()
        if not Path(path).is_file():
            QMessageBox.information(self, "Choose a video", "Choose an existing final MP4 first.")
            return
        if self.player.source().toLocalFile() != str(Path(path).resolve()):
            self._load_video(path)
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.play.setText("Resume playback")
        else:
            self.player.play()
            self.play.setText("Pause playback")

    def _platform_changed(self, *_args):
        self.review.setChecked(False)
        platform = self._platform_key()
        self.privacy.setVisible(platform == "youtube")
        self.tags.setVisible(platform == "youtube")
        self.public_url.setVisible(platform == "instagram")
        self.account.setVisible(platform == "facebook")
        self._refresh_accounts()
        self._update_publish_enabled()

    def _refresh_accounts(self):
        key = self._platform_key()
        self.account.clear()
        accounts = publishing.connected_accounts()
        if key == "facebook":
            for page in accounts["facebook_pages"]:
                self.account.addItem(page["name"], page["id"])
        elif key == "instagram" and accounts["instagram"]:
            self.account.addItem("@" + accounts["instagram"], accounts["instagram"])
        elif key == "youtube" and accounts["youtube"]:
            self.account.addItem("Connected YouTube account", "youtube")
        if key != "facebook":
            self.account.setVisible(False)

    def _open_settings(self):
        dialog = PublishSettingsDialog(self)
        dialog.exec()
        self._refresh_accounts()

    def _connect(self):
        platform = self._platform_key()
        if self._worker and self._worker.isRunning():
            return
        work = {
            "youtube": publishing.connect_youtube,
            "instagram": publishing.connect_instagram,
            "facebook": publishing.connect_facebook,
        }[platform]
        self.connect_button.setEnabled(False)
        self.result.setText("Opening the official platform sign-in flow…")
        self._worker = _SocialWorker(work, self)
        self._worker.succeeded.connect(self._connected)
        self._worker.failed.connect(self._failed)
        self._worker.finished.connect(lambda: self.connect_button.setEnabled(True))
        self._worker.start()

    def _connected(self, outcome):
        if isinstance(outcome, list):
            self._refresh_accounts()
            if outcome:
                self.account.setCurrentIndex(0)
            self.result.setText(f"Connected {len(outcome)} Facebook Page(s). Choose the Page to publish from.")
        else:
            self._refresh_accounts()
            self.result.setText(str(outcome))

    def _update_publish_enabled(self, *_args):
        path = Path(self.video_path.text().strip())
        correct_url = self._platform_key() != "instagram" or self.public_url.text().strip().startswith("https://")
        accounts = publishing.connected_accounts()
        connected = {
            "youtube": accounts["youtube"],
            "instagram": bool(accounts["instagram"]),
            "facebook": bool(self.account.currentData()),
        }[self._platform_key()]
        self.publish.setEnabled(
            bool(
                path.is_file()
                and path.suffix.casefold() == ".mp4"
                and self.title.text().strip()
                and self.review.isChecked()
                and self.review.isEnabled()
                and correct_url
                and connected
            )
        )

    def _publish(self):
        platform = self._platform_key()
        path = Path(self.video_path.text().strip()).expanduser()
        if not path.is_file():
            QMessageBox.warning(self, "Missing video", "Choose the final MP4 export you reviewed.")
            return
        if platform == "instagram" and not self.public_url.text().strip().startswith("https://"):
            QMessageBox.warning(self, "Instagram media URL required", "Provide the public HTTPS URL for this exact reviewed MP4.")
            return
        if not self.review.isEnabled() or not self.review.isChecked():
            QMessageBox.warning(self, "Review required", "Play the entire export and check the approval box before publishing.")
            return
        details = {
            "title": self.title.text().strip(),
            "description": self.description.toPlainText().strip(),
            "tags": self.tags.text(),
            "privacy": self.privacy.currentText().casefold(),
            "public_url": self.public_url.text().strip(),
            "page_id": self.account.currentData() or "",
        }
        confirmed = QMessageBox.question(
            self,
            "Confirm publication",
            f"Publish this reviewed video now to {self.platform.currentText()}? "
            "This will send the video and caption to the selected account.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmed != QMessageBox.Yes:
            return
        self.publish.setEnabled(False)
        self.result.setText("Uploading and publishing through the official platform API…")
        self._worker = _SocialWorker(lambda: publishing.publish_video(platform, path, details), self)
        self._worker.succeeded.connect(self._published)
        self._worker.failed.connect(self._failed)
        self._worker.finished.connect(self._update_publish_enabled)
        self._worker.start()

    def _published(self, url):
        self._published_url = str(url)
        self.result.setText(f"Published successfully: <a href=\"{url}\">{url}</a>")
        self.result.setOpenExternalLinks(True)
        self.review.setChecked(False)
        self.review.setEnabled(False)
        self._watched_bins.clear()
        self._finished = False
        QMessageBox.information(self, "Published", f"Your video was published:\n{url}")

    def _failed(self, message):
        QMessageBox.critical(self, "Publishing failed", message)
        self.result.setText("Publishing failed. The platform may still be processing the request; check the account before retrying.")
        self._update_publish_enabled()

    def closeEvent(self, event):
        self.player.stop()
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "Publishing in progress", "Wait for the current platform request to finish before closing.")
            event.ignore()
            return
        event.accept()


class PublishSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Social Publishing Settings")
        self.setMinimumWidth(620)
        self._worker = None

        google_status = QLabel("Google OAuth: configured" if publishing._get("google-client") else "Google OAuth: not configured")
        google_file = QPushButton("Choose Google OAuth client-secrets JSON…")
        google_file.clicked.connect(lambda: self._choose_google_client(google_status))
        meta = publishing._json("meta-client")
        self.meta_id = QLineEdit(meta.get("app_id", ""))
        self.meta_id.setPlaceholderText("Meta App ID")
        self.meta_secret = QLineEdit(meta.get("app_secret", ""))
        self.meta_secret.setPlaceholderText("Meta App Secret")
        self.meta_secret.setEchoMode(QLineEdit.Password)
        save_meta = QPushButton("Save Meta app credentials")
        save_meta.clicked.connect(self._save_meta)

        redirect = QLabel(
            "For Meta Login, add this exact redirect URI in your Meta developer app:\n"
            + publishing.FACEBOOK_REDIRECT_URI
            + "\nEnable Instagram Login with instagram_business_basic and instagram_business_content_publish; "
            "enable Facebook Login with pages_show_list, pages_read_engagement, and pages_manage_posts."
        )
        redirect.setWordWrap(True)
        self.account_status = QLabel()
        self.account_status.setWordWrap(True)
        self._update_status()
        close = QPushButton("Done")
        close.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("YouTube"))
        layout.addWidget(google_status)
        layout.addWidget(google_file)
        layout.addSpacing(10)
        layout.addWidget(QLabel("Instagram and Facebook Pages"))
        layout.addWidget(self.meta_id)
        layout.addWidget(self.meta_secret)
        layout.addWidget(save_meta)
        layout.addWidget(redirect)
        layout.addWidget(self.account_status)
        layout.addWidget(close, alignment=Qt.AlignRight)

    def _choose_google_client(self, status):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Google OAuth client JSON", "", "JSON (*.json)")
        if not path:
            return
        try:
            client = json.loads(Path(path).read_text(encoding="utf-8"))
            publishing.save_google_client(client)
            status.setText("Google OAuth client saved securely in the Windows credential store.")
        except Exception as exc:
            QMessageBox.critical(self, "Invalid Google client", str(exc))

    def _save_meta(self):
        try:
            publishing.save_meta_client(self.meta_id.text(), self.meta_secret.text())
            self.account_status.setText("Meta credentials saved securely in the Windows credential store.")
        except Exception as exc:
            QMessageBox.critical(self, "Could not save Meta credentials", str(exc))

    def _update_status(self):
        accounts = publishing.connected_accounts()
        page_names = ", ".join(page["name"] for page in accounts["facebook_pages"]) or "No Facebook Pages connected"
        self.account_status.setText(
            f"YouTube: {'connected' if accounts['youtube'] else 'not connected'} · "
            f"Instagram: {('@' + accounts['instagram']) if accounts['instagram'] else 'not connected'} · "
            f"Facebook: {page_names}"
        )
