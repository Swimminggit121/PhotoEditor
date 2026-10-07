from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from PIL import Image

from image.loader import is_supported, is_raw, load_image, load_preview


@dataclass(frozen=True)
class PhotoDuplicateGroup:
    paths: tuple[Path, ...]
    similarity: float


def collect_photo_paths(
    inputs: list[str | Path],
    recursive: bool = True,
) -> list[Path]:
    found: dict[str, Path] = {}
    for input_path in inputs:
        path = Path(input_path).expanduser().resolve()
        if path.is_dir():
            iterator = path.rglob("*") if recursive else path.iterdir()
            candidates = (item for item in iterator if item.is_file())
        elif path.is_file():
            candidates = (path,)
        else:
            raise ValueError(f"Photo input does not exist: {path}")
        for candidate in candidates:
            if is_supported(candidate):
                found.setdefault(str(candidate.resolve()).casefold(), candidate.resolve())
    return sorted(found.values(), key=lambda item: str(item).casefold())


def load_oriented_photo(path: str | Path) -> Image.Image:
    return load_image(path)


def _photo_signatures(path: Path) -> tuple[int, int, np.ndarray]:
    try:
        image = load_preview(path, max_dimension=512).convert("RGB")
        gray = image.convert("L")
        sample = np.asarray(gray.resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float32)
    except Exception as exc:
        raise RuntimeError(f"Could not analyze photo content in {path.name}: {exc}") from exc

    coefficients = cv2.dct(sample)[:8, :8].reshape(-1)
    median = float(np.median(coefficients[1:]))
    perceptual = 0
    for bit in coefficients:
        perceptual = (perceptual << 1) | int(float(bit) > median)

    difference_sample = np.asarray(gray.resize((9, 8), Image.Resampling.LANCZOS), dtype=np.uint8)
    difference = 0
    for bit in (difference_sample[:, 1:] > difference_sample[:, :-1]).reshape(-1):
        difference = (difference << 1) | int(bit)

    color_sample = np.asarray(image.resize((16, 16), Image.Resampling.BILINEAR), dtype=np.uint8)
    mean_lab = cv2.cvtColor(color_sample, cv2.COLOR_RGB2LAB).mean(axis=(0, 1))
    return perceptual, difference, mean_lab


def find_duplicate_groups(
    paths: list[str | Path],
    threshold: int = 6,
    progress: Callable[[int, int, Path], None] | None = None,
) -> list[PhotoDuplicateGroup]:
    if not 0 <= threshold <= 16:
        raise ValueError("Perceptual duplicate threshold must be between 0 and 16.")
    photos = [Path(path).expanduser().resolve() for path in paths]
    if len(photos) < 2:
        return []

    hashes = []
    difference_hashes = []
    colors = []
    buckets: dict[tuple[str, int, int], list[int]] = defaultdict(list)
    for index, path in enumerate(photos):
        value, difference_hash, color = _photo_signatures(path)
        hashes.append(value)
        difference_hashes.append(difference_hash)
        colors.append(color)
        if progress:
            progress(index + 1, len(photos), path)

    parents = list(range(len(photos)))

    def root(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def join(first: int, second: int) -> None:
        left, right = root(first), root(second)
        if left != right:
            parents[right] = left

    distances: dict[tuple[int, int], int] = {}
    for index, value in enumerate(hashes):
        candidates: set[int] = set()
        for kind, signature in (("p", value), ("d", difference_hashes[index])):
            for band in range(8):
                shift = band * 8
                candidates.update(buckets[(kind, band, (signature >> shift) & 0xFF)])
        for other in candidates:
            distance = min(
                (value ^ hashes[other]).bit_count(),
                (difference_hashes[index] ^ difference_hashes[other]).bit_count(),
            )
            color_distance = float(np.linalg.norm(colors[index] - colors[other]))
            if distance <= threshold and color_distance <= 22:
                pair = (other, index)
                distances[pair] = distance
                join(other, index)
        for kind, signature in (("p", value), ("d", difference_hashes[index])):
            for band in range(8):
                shift = band * 8
                buckets[(kind, band, (signature >> shift) & 0xFF)].append(index)

    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(photos)):
        groups[root(index)].append(index)

    duplicates = []
    for members in groups.values():
        if len(members) < 2:
            continue
        member_set = set(members)
        group_distances = [
            distance for (first, second), distance in distances.items()
            if first in member_set and second in member_set
        ]
        similarity = 100.0 * (1.0 - max(group_distances or [threshold]) / 64)
        duplicates.append(
            PhotoDuplicateGroup(
                tuple(photos[index] for index in members),
                round(similarity, 1),
            )
        )
    return sorted(duplicates, key=lambda group: str(group.paths[0]).casefold())
