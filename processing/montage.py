from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from PIL import Image

from core.auto_grade import auto_edit
from core.renderer import render_image
from image.loader import is_raw
from processing.photo_duplicates import collect_photo_paths, load_oriented_photo
from processing.video_render import mux_montage_audio


TEMPLATES = {
    "Cinematic push": (2.6, 0.65, "cinematic"),
    "Story drift": (2.2, 0.5, "story"),
    "Dynamic snap": (0.8, 0.0, "snap"),
    "Memory flash": (1.5, 0.22, "flash"),
}


def _prepare_photo(
    path: Path,
    width: int,
    height: int,
    adjustments=None,
    auto_grade_photos: bool = False,
) -> np.ndarray:
    rgb = load_oriented_photo(path)
    if auto_grade_photos:
        suffix = path.suffix.casefold()
        file_kind = "raw" if is_raw(path) else {
            ".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png",
            ".tif": "tif", ".tiff": "tiff", ".webp": "webp",
        }.get(suffix, "generic")
        rgb = render_image(rgb, auto_edit(rgb, file_kind=file_kind))
    if adjustments is not None:
        max_source_size = max(width, height) * 2
        if max(rgb.size) > max_source_size:
            scale = max_source_size / max(rgb.size)
            rgb = rgb.resize(
                (max(1, int(rgb.width * scale)), max(1, int(rgb.height * scale))),
                Image.Resampling.LANCZOS,
            )
        rgb = render_image(rgb, adjustments)
    max_scale = max(width / rgb.width, height / rgb.height)
    resized = rgb.resize(
        (max(1, int(rgb.width * max_scale)), max(1, int(rgb.height * max_scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGB", (width, height), (0, 0, 0))
    left = (width - resized.width) // 2
    top = (height - resized.height) // 2
    canvas.paste(resized, (left, top))
    return np.asarray(canvas, dtype=np.uint8)


def _motion_frame(image: np.ndarray, progress: float, style: str, index: int) -> np.ndarray:
    height, width = image.shape[:2]
    direction = 1 if index % 2 == 0 else -1
    if style == "cinematic":
        zoom = 1.0 + 0.12 * progress
        drift_x, drift_y = direction * progress * 0.035, -progress * 0.025
    elif style == "story":
        zoom = 1.08 - 0.045 * progress
        drift_x, drift_y = -direction * progress * 0.045, progress * 0.02
    elif style == "snap":
        zoom = 1.02 + 0.12 * progress
        drift_x, drift_y = direction * progress * 0.055, 0.0
    else:
        zoom = 1.015 + 0.04 * progress
        drift_x, drift_y = 0.0, 0.0

    crop_width = max(1, int(width / zoom))
    crop_height = max(1, int(height / zoom))
    center_x = int(width * (0.5 + drift_x))
    center_y = int(height * (0.5 + drift_y))
    left = min(max(0, center_x - crop_width // 2), width - crop_width)
    top = min(max(0, center_y - crop_height // 2), height - crop_height)
    crop = image[top:top + crop_height, left:left + crop_width]
    return cv2.resize(crop, (width, height), interpolation=cv2.INTER_CUBIC)


def _transition_frame(current: np.ndarray, following: np.ndarray, progress: float, style: str) -> np.ndarray:
    if style != "flash":
        return cv2.addWeighted(current, 1.0 - progress, following, progress, 0)
    if progress < 0.5:
        return cv2.addWeighted(current, 1.0 - progress * 2, np.full_like(current, 255), progress * 2, 0)
    return cv2.addWeighted(np.full_like(following, 255), 1.0 - (progress - 0.5) * 2, following, (progress - 0.5) * 2, 0)


def generate_reel_video(
    input_dir: str | Path | None,
    output_file: str | Path,
    fps: int = 30,
    duration_per_photo: float = 2.5,
    transition_duration: float = 0.8,
    aspect_ratio: str = "9:16",
    width: int | None = None,
    height: int | None = None,
    audio_path: str | Path | None = None,
    audio_volume: float = 0.35,
    adjustments=None,
    photo_paths: list[str | Path] | None = None,
    recursive: bool = True,
    template: str | None = None,
    auto_grade_photos: bool = False,
    progress=None,
):
    if template is not None:
        if template not in TEMPLATES:
            raise ValueError(f"Unknown photo montage template: {template}")
        _, _, motion_style = TEMPLATES[template]
    else:
        motion_style = "story"

    inputs = photo_paths if photo_paths is not None else ([input_dir] if input_dir else [])
    image_paths = collect_photo_paths(inputs, recursive=recursive)
    if not image_paths:
        raise ValueError("No supported photos were found in the selected files or folders.")
    if not audio_path:
        raise ValueError("Choose a licensed soundtrack or audio file; every montage must include audio.")
    if not Path(audio_path).expanduser().is_file():
        raise ValueError(f"Soundtrack file not found: {audio_path}")
    if fps <= 0 or duration_per_photo <= 0 or transition_duration < 0:
        raise ValueError("FPS and photo duration must be positive; transition duration cannot be negative.")
    if not 0 <= audio_volume <= 2:
        raise ValueError("Soundtrack volume must be between 0 and 2.")

    ratio = {
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
        "4:5": (1080, 1350),
        "16:9": (1920, 1080),
        "4:3": (1440, 1080),
    }.get(aspect_ratio, (1080, 1920))
    target_width = width or ratio[0]
    target_height = height or ratio[1]

    output_path = Path(output_file).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() not in {".mp4", ".mov", ".avi"}:
        output_path = output_path.with_suffix(".mp4")

    silent_path = output_path
    if audio_path:
        if output_path.suffix.casefold() not in {".mp4", ".mov"}:
            raise ValueError("Choose an MP4 or MOV output file when adding a soundtrack.")
        silent_path = output_path.with_name(f".{output_path.stem}-{uuid4().hex}.silent.mp4")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(silent_path), fourcc, fps, (target_width, target_height))
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not create the output video file.")

    total_frames = (
        len(image_paths) * max(1, int(round(duration_per_photo * fps)))
        + max(0, len(image_paths) - 1) * max(0, int(round(transition_duration * fps)))
    )
    completed_frames = 0
    try:
        current = None
        for index, image_path in enumerate(image_paths):
            if current is None:
                current = _prepare_photo(
                    image_path, target_width, target_height, adjustments,
                    auto_grade_photos=auto_grade_photos,
                )
            hold_frames = max(1, int(round(duration_per_photo * fps)))
            for step in range(hold_frames):
                progress_ratio = step / max(1, hold_frames - 1)
                writer.write(_motion_frame(current, progress_ratio, motion_style, index))
                completed_frames += 1
                if progress:
                    progress(completed_frames, total_frames, image_path.name)

            if index == len(image_paths) - 1:
                continue

            next_image = _prepare_photo(
                image_paths[index + 1], target_width, target_height, adjustments,
                auto_grade_photos=auto_grade_photos,
            )
            transition_frames = max(0, int(round(transition_duration * fps)))
            for step in range(transition_frames):
                alpha = (step + 1) / transition_frames
                outgoing = _motion_frame(current, alpha, motion_style, index)
                incoming = _motion_frame(next_image, alpha, motion_style, index + 1)
                writer.write(_transition_frame(outgoing, incoming, alpha, motion_style))
                completed_frames += 1
                if progress:
                    progress(completed_frames, total_frames, image_paths[index + 1].name)
            current = next_image
    finally:
        writer.release()

    if audio_path:
        try:
            mux_montage_audio(silent_path, audio_path, output_path, audio_volume)
        finally:
            silent_path.unlink(missing_ok=True)
    return output_path
