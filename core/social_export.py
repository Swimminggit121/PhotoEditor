from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


@dataclass(frozen=True)
class SocialProfile:
    key: str
    label: str
    width: int
    height: int
    folder: str
    suffix: str


PROFILES = {
    "instagram_portrait": SocialProfile("instagram_portrait", "Instagram Portrait 4:5", 1080, 1350, "Instagram_4x5", "_instagram_4x5.jpg"),
    "square": SocialProfile("square", "Square 1:1", 1080, 1080, "Square_1x1", "_square.jpg"),
    "vertical": SocialProfile("vertical", "Reel / Short / Story 9:16", 1080, 1920, "Vertical_9x16", "_vertical_9x16.jpg"),
    "landscape": SocialProfile("landscape", "YouTube / Landscape 16:9", 1920, 1080, "Landscape_16x9", "_landscape_16x9.jpg"),
}


def _fit(image: Image.Image, width: int, height: int, focal_point: tuple[float, float] = (0.5, 0.5)) -> Image.Image:
    focal_x = max(0.0, min(1.0, float(focal_point[0])))
    focal_y = max(0.0, min(1.0, float(focal_point[1])))
    return ImageOps.fit(
        image.convert("RGB"),
        (int(width), int(height)),
        method=Image.Resampling.LANCZOS,
        centering=(focal_x, focal_y),
    )


def export_social_image(
    image: Image.Image,
    destination: str | Path,
    profile: SocialProfile,
    quality: int = 95,
    focal_point: tuple[float, float] = (0.5, 0.5),
    metadata: bytes | None = None,
) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    kwargs = dict(format="JPEG", quality=max(1, min(100, int(quality))), optimize=True, progressive=True)
    if metadata:
        kwargs["exif"] = metadata
    _fit(image, profile.width, profile.height, focal_point).save(destination, **kwargs)
    return destination


def export_social_pack(
    image: Image.Image,
    source_stem: str,
    output_dir: str | Path,
    quality: int = 95,
    profiles: tuple[str, ...] = tuple(PROFILES),
    focal_point: tuple[float, float] = (0.5, 0.5),
    metadata: bytes | None = None,
) -> list[Path]:
    output_dir = Path(output_dir)
    results = []
    for key in profiles:
        profile = PROFILES[key]
        results.append(
            export_social_image(
                image,
                output_dir / profile.folder / f"{source_stem}{profile.suffix}",
                profile,
                quality,
                focal_point,
                metadata,
            )
        )
    return results


def _ken_burns_frame(image: Image.Image, width: int, height: int, progress: float) -> np.ndarray:
    source = image.convert("RGB")
    target_ratio = width / height
    source_ratio = source.width / max(source.height, 1)
    if source_ratio > target_ratio:
        crop_h, crop_w = source.height, int(source.height * target_ratio)
    else:
        crop_w, crop_h = source.width, int(source.width / target_ratio)

    max_x = max(0, source.width - crop_w)
    max_y = max(0, source.height - crop_h)
    zoom = 1.0 + 0.045 * float(progress)
    crop_w = max(2, min(source.width, int(crop_w / zoom)))
    crop_h = max(2, min(source.height, int(crop_h / zoom)))
    x = max(0, min(int(max_x * (0.15 + 0.70 * progress)), source.width - crop_w))
    y = max(0, min(int(max_y * (0.20 + 0.55 * progress)), source.height - crop_h))
    frame = source.crop((x, y, x + crop_w, y + crop_h)).resize((width, height), Image.Resampling.LANCZOS)
    return cv2.cvtColor(np.asarray(frame), cv2.COLOR_RGB2BGR)


def create_social_slideshow_from_paths(
    image_paths: list[str | Path],
    destination: str | Path,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    seconds_per_photo: float = 2.0,
    transition_seconds: float = 0.25,
) -> Path:
    if not image_paths:
        raise ValueError("At least one photo is required to create a social clip.")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fps = max(1, int(fps))
    seconds_per_photo = max(0.5, float(seconds_per_photo))
    transition_frames = min(int(round(max(0.0, min(transition_seconds, seconds_per_photo * 0.5)) * fps)), max(0, int(seconds_per_photo * fps) // 2))
    frames_per_photo = max(1, int(round(seconds_per_photo * fps)))

    writer = cv2.VideoWriter(str(destination), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("Could not create the MP4 video. Check that OpenCV has an MP4 codec available.")

    try:
        previous = None
        for path in image_paths:
            with Image.open(path) as opened:
                current = opened.convert("RGB")
            if previous is not None:
                _write_photo(writer, previous, current, width, height, frames_per_photo, transition_frames)
            previous = current
        if previous is not None:
            _write_photo(writer, previous, None, width, height, frames_per_photo, 0)
    finally:
        writer.release()
    return destination


def _write_photo(writer, image, next_image, width, height, frames_per_photo, transition_frames):
    for frame_index in range(frames_per_photo):
        progress = frame_index / max(frames_per_photo - 1, 1)
        current = _ken_burns_frame(image, width, height, progress)
        if next_image is not None and transition_frames and frame_index >= frames_per_photo - transition_frames:
            next_progress = (frame_index - (frames_per_photo - transition_frames)) / max(transition_frames - 1, 1)
            following = _ken_burns_frame(next_image, width, height, next_progress)
            current = cv2.addWeighted(current, 1.0 - next_progress, following, next_progress, 0.0)
        writer.write(current)
