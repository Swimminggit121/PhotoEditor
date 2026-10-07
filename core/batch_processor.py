from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable

from core.auto_grade import auto_colour_grade, auto_edit
from core.document import Document
from image.export import export_image
from image.loader import is_supported

EXPORTABLE_EXTENSIONS={".jpg",".jpeg",".png",".tif",".tiff",".webp"}

ProgressCallback = Callable[[int, int, Path], None]


@dataclass
class BatchResult:
    processed: list[Path]
    failed: list[tuple[Path, str]]
    cancelled: bool = False
    social_exports: list[Path] | None = None
    slideshow: Path | None = None


class BatchProcessor:
    """Process large photo sets without changing the source files."""

    def __init__(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        mode: str = "auto_edit",
        quality: int = 95,
        recursive: bool = False,
        preset=None,
        reference=None,
        social_pack: bool = False,
        create_slideshow: bool = False,
        slideshow_seconds: float = 2.0,
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.mode = mode
        self.quality = int(max(1, min(100, quality)))
        self.recursive = recursive
        self.preset = preset
        self.reference = reference
        self.social_pack = bool(social_pack)
        self.create_slideshow = bool(create_slideshow)
        self.slideshow_seconds = max(0.5, float(slideshow_seconds))
        self.cancel_event = Event()

    def cancel(self):
        self.cancel_event.set()

    def files(self) -> list[Path]:
        iterator = self.input_dir.rglob("*") if self.recursive else self.input_dir.iterdir()
        return sorted(p for p in iterator if p.is_file() and is_supported(p))

    def _adjustments_for(self, document: Document):
        if self.mode == "auto_edit":
            return auto_edit(document.original_image, document.adjustments)
        if self.mode == "auto_grade":
            return auto_colour_grade(document.original_image, document.adjustments)
        if self.mode == "preset":
            if self.preset is None:
                raise ValueError("No preset was selected.")
            return self.preset.copy()
        if self.mode == "reference":
            if self.reference is None:
                raise ValueError("No reference style was selected.")
            from core.style_match import apply_style_profile
            return apply_style_profile(document.original_image, self.reference)
        raise ValueError(f"Unknown batch mode: {self.mode}")

    def run(self, progress: ProgressCallback | None = None) -> BatchResult:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        source_files = self.files()
        processed: list[Path] = []
        failed: list[tuple[Path, str]] = []
        social_exports: list[Path] = []
        slideshow_images = []

        for index, source in enumerate(source_files, 1):
            if self.cancel_event.is_set():
                return BatchResult(processed, failed, True, social_exports, None)

            try:
                document = Document()
                document.load(source)
                document.adjustments = self._adjustments_for(document)
                rendered = document.render()

                relative = source.relative_to(self.input_dir) if self.recursive else Path(source.name)
                destination = self.output_dir / "Edited" / relative
                suffix=destination.suffix.lower()
                if suffix not in EXPORTABLE_EXTENSIONS:
                    destination=destination.with_suffix(".jpg")
                destination=destination.with_name(destination.stem + "_edited" + destination.suffix)
                destination.parent.mkdir(parents=True, exist_ok=True)

                export_image(rendered, destination, self.quality)
                processed.append(destination)

                if self.social_pack:
                    from core.social_export import export_social_pack
                    social_exports.extend(
                        export_social_pack(
                            rendered,
                            source.stem,
                            self.output_dir / "Social_Pack",
                            self.quality,
                        )
                    )

                if self.create_slideshow:
                    slideshow_images.append(rendered.copy())
            except Exception as exc:
                failed.append((source, str(exc)))

            if progress:
                progress(index, len(source_files), source)

        slideshow = None
        if self.create_slideshow and slideshow_images and not self.cancel_event.is_set():
            try:
                from core.social_export import create_social_slideshow
                slideshow = create_social_slideshow(
                    slideshow_images,
                    self.output_dir / "Social_Video" / "vertical_social_clip.mp4",
                    seconds_per_photo=self.slideshow_seconds,
                )
            except Exception as exc:
                failed.append((Path("social slideshow"), str(exc)))

        return BatchResult(processed, failed, False, social_exports, slideshow)
