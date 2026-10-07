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


def _fit(image: Image.Image, width: int, height: int) -> Image.Image:
    return ImageOps.fit(
        image.convert("RGB"),
        (int(width), int(height)),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def export_social_image(image: Image.Image, destination: str | Path, profile: SocialProfile, quality: int = 95) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fitted = _fit(image, profile.width, profile.height)
    fitted.save(
        destination,
        format="JPEG",
        quality=max(1, min(100, int(quality))),
        optimize=True,
        progressive=True,
    )
    return destination


def export_social_pack(
    image: Image.Image,
    source_stem: str,
    output_dir: str | Path,
    quality: int = 95,
    profiles: tuple[str, ...] = tuple(PROFILES),
) -> list[Path]:
    output_dir = Path(output_dir)
    results: list[Path] = []
    for key in profiles:
        profile = PROFILES[key]
        target = output_dir / profile.folder / f"{source_stem}{profile.suffix}"
        results.append(export_social_image(image, target, profile, quality))
    return results


def _ken_burns_frame(image: Image.Image, width: int, height: int, progress: float) -> np.ndarray:
    source = image.convert("RGB")
    target_ratio = width / height
    source_ratio = source.width / max(source.height, 1)

    if source_ratio > target_ratio:
        crop_h = source.height
        crop_w = int(crop_h * target_ratio)
    else:
        crop_w = source.width
        crop_h = int(crop_w / target_ratio)

    max_x = max(0, source.width - crop_w)
    max_y = max(0, source.height - crop_h)

    # Slow zoom plus a gentle diagonal pan keeps still-photo videos alive without
    # introducing distracting motion.
    zoom = 1.0 + 0.045 * float(progress)
    crop_w = max(2, min(source.width, int(crop_w / zoom)))
    crop_h = max(2, min(source.height, int(crop_h / zoom)))
    x = int(max_x * (0.15 + 0.70 * progress))
    y = int(max_y * (0.20 + 0.55 * progress))
    x = max(0, min(x, source.width - crop_w))
    y = max(0, min(y, source.height - crop_h))

    frame = source.crop((x, y, x + crop_w, y + crop_h)).resize(
        (width, height), Image.Resampling.LANCZOS
    )
    return cv2.cvtColor(np.asarray(frame), cv2.COLOR_RGB2BGR)


def create_social_slideshow(
    images: list[Image.Image],
    destination: str | Path,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    seconds_per_photo: float = 2.0,
    transition_seconds: float = 0.25,
) -> Path:
    if not images:
        raise ValueError("At least one photo is required to create a social clip.")

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    fps = max(1, int(fps))
    seconds_per_photo = max(0.5, float(seconds_per_photo))
    transition_seconds = max(0.0, min(float(transition_seconds), seconds_per_photo * 0.5))
    frames_per_photo = max(1, int(round(seconds_per_photo * fps)))
    transition_frames = min(
        int(round(transition_seconds * fps)),
        max(0, frames_per_photo // 2),
    )

    writer = cv2.VideoWriter(
        str(destination),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (int(width), int(height)),
    )
    if not writer.isOpened():
        raise RuntimeError("Could not create the MP4 video. Check that OpenCV has an MP4 codec available.")

    try:
        prepared = [image.convert("RGB") for image in images]

        for index, image in enumerate(prepared):
            for frame_index in range(frames_per_photo):
                progress = frame_index / max(frames_per_photo - 1, 1)
                current = _ken_burns_frame(image, width, height, progress)

                if (
                    transition_frames > 0
                    and frame_index >= frames_per_photo - transition_frames
                    and index < len(prepared) - 1
                ):
                    next_image = prepared[index + 1]
                    next_progress = (
                        frame_index - (frames_per_photo - transition_frames)
                    ) / max(transition_frames - 1, 1)
                    following = _ken_burns_frame(next_image, width, height, next_progress)
                    alpha = float(np.clip(next_progress, 0.0, 1.0))
                    current = cv2.addWeighted(current, 1.0 - alpha, following, alpha, 0.0)

                writer.write(current)
    finally:
        writer.release()

    return destination
