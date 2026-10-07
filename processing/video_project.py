from __future__ import annotations

import json
import math
import re
import subprocess
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import uuid4

import cv2


@dataclass
class TimelineClip:
    path: str
    kind: str
    start: float
    duration: float
    source_in: float = 0.0
    track: int = 0
    volume: float = 1.0
    include_source_audio: bool = True
    title: str = ""
    opacity: float = 1.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    clip_id: str = field(default_factory=lambda: uuid4().hex)

    @property
    def end(self) -> float:
        return self.start + self.duration


@dataclass
class VideoProject:
    name: str = "Untitled video"
    width: int = 1920
    height: int = 1080
    fps: int = 30
    background: str = "#101010"
    clips: list[TimelineClip] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max((clip.end for clip in self.clips), default=0.0)

    def add_media(self, path: str | Path, track: int = 0) -> TimelineClip:
        media = Path(path).expanduser().resolve()
        if not media.is_file():
            raise ValueError(f"Media file not found: {media}")
        kind = classify_media(media)
        media_duration = get_media_duration(media, kind)
        start = max((clip.end for clip in self.clips if clip.track == track), default=0.0)
        clip = TimelineClip(str(media), kind, start, media_duration, track=track)
        self.clips.append(clip)
        return clip

    def add_title(self, text: str, track: int = 1, duration: float = 4.0) -> TimelineClip:
        title = text.strip()
        if not title:
            raise ValueError("Enter title text before adding a title clip.")
        start = max((clip.end for clip in self.clips if clip.track == track), default=0.0)
        clip = TimelineClip("", "title", start, duration, track=track, title=title, fade_in=0.3, fade_out=0.3)
        self.clips.append(clip)
        return clip

    def remove(self, clip_id: str) -> None:
        self.clips = [clip for clip in self.clips if clip.clip_id != clip_id]

    def clip(self, clip_id: str) -> TimelineClip:
        for item in self.clips:
            if item.clip_id == clip_id:
                return item
        raise KeyError(f"Unknown timeline clip: {clip_id}")

    def save(self, path: str | Path) -> Path:
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "background": self.background,
            "clips": [asdict(clip) for clip in self.clips],
        }
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> VideoProject:
        source = Path(path).expanduser().resolve()
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not read video project: {exc}") from exc
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("clips"), list):
            raise ValueError("Unsupported or invalid video project file.")
        clips = []
        for item in data["clips"]:
            clip = TimelineClip(**item)
            if clip.kind != "title" and not Path(clip.path).is_file():
                raise ValueError(f"Project media is missing: {clip.path}")
            clips.append(clip)
        project = cls(
            name=str(data.get("name", source.stem)),
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
            fps=int(data.get("fps", 30)),
            background=str(data.get("background", "#101010")),
            clips=clips,
        )
        validate_project(project)
        return project


def classify_media(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}:
        return "image"
    if suffix in {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}:
        return "audio"
    if suffix in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mts", ".m2ts"}:
        return "video"
    raise ValueError(f"Unsupported video-editor media type: {path.suffix or '(no extension)'}")


def get_media_duration(path: Path, kind: str) -> float:
    if kind == "image":
        return 5.0
    if kind == "audio" and path.suffix.casefold() == ".wav":
        with wave.open(str(path), "rb") as stream:
            return stream.getnframes() / stream.getframerate()
    if kind == "video":
        capture = cv2.VideoCapture(str(path))
        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
            if fps > 0 and frames > 0:
                return frames / fps
        finally:
            capture.release()
    if kind in {"video", "audio"}:
        from processing.video_render import ffmpeg_path

        probe = subprocess.run(
            [ffmpeg_path(), "-hide_banner", "-i", str(path)],
            capture_output=True, text=True, check=False,
        )
        match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", probe.stderr)
        if match:
            hours, minutes, seconds = match.groups()
            return max(0.1, int(hours) * 3600 + int(minutes) * 60 + float(seconds))
        raise ValueError(f"Could not read the duration of media file: {path.name}")
    raise ValueError(f"Cannot determine duration for media type: {kind}")


def validate_project(project: VideoProject) -> None:
    if (
        not isinstance(project.width, int) or not isinstance(project.height, int)
        or not (2 <= project.width <= 7680 and 2 <= project.height <= 4320)
        or project.width % 2 or project.height % 2
    ):
        raise ValueError("Project resolution must use even dimensions between 2×2 and 7680×4320.")
    if not isinstance(project.fps, int) or not (1 <= project.fps <= 120):
        raise ValueError("Project frame rate must be between 1 and 120 FPS.")
    if not project.clips:
        raise ValueError("Add at least one media clip before exporting.")
    if not isinstance(project.background, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", project.background):
        raise ValueError("Project background must be a six-digit hexadecimal colour.")
    if len({clip.clip_id for clip in project.clips}) != len(project.clips):
        raise ValueError("Timeline clips must have unique IDs.")
    for clip in project.clips:
        if clip.kind not in {"image", "video", "audio", "title"}:
            raise ValueError(f"Unsupported timeline clip type: {clip.kind}")
        numeric = (clip.start, clip.duration, clip.source_in, clip.volume, clip.opacity, clip.fade_in, clip.fade_out)
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) for value in numeric):
            raise ValueError("Timeline positions and trims must be finite numbers.")
        if clip.start < 0 or clip.duration <= 0 or clip.source_in < 0:
            raise ValueError("Timeline clips need non-negative start/trim and positive duration.")
        if not isinstance(clip.track, int) or clip.track < 0:
            raise ValueError("Track numbers must be non-negative integers.")
        if not 0 <= clip.volume <= 2:
            raise ValueError("Clip volume must be between 0 and 200%.")
        if not 0 <= clip.opacity <= 1:
            raise ValueError("Clip opacity must be between 0 and 100%.")
        if not 0 <= clip.fade_in <= clip.duration or not 0 <= clip.fade_out <= clip.duration:
            raise ValueError("Clip fades must fit within the clip duration.")
        if clip.kind == "title" and not clip.title.strip():
            raise ValueError("Title clips need text.")
        if clip.kind == "title" and len(clip.title) > 500:
            raise ValueError("Title text is limited to 500 characters.")
        if clip.kind != "title":
            try:
                media_path = Path(clip.path)
                actual_kind = classify_media(media_path)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid media path for timeline clip: {exc}") from exc
            if not media_path.is_file():
                raise ValueError(f"Timeline media file is missing: {media_path}")
            if actual_kind != clip.kind:
                raise ValueError(f"{media_path.name} is not a {clip.kind} file.")
