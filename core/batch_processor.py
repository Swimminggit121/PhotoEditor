from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable

from core.auto_grade import auto_colour_grade, auto_edit
from core.document import Document
from image.export import ExportRecipe, export_image, export_with_recipe, srgb_profile_bytes
from image.loader import is_raw, is_supported

EXPORTABLE_EXTENSIONS={".jpg",".jpeg",".png",".tif",".tiff",".webp"}

ProgressCallback = Callable[[int, int, Path], None]


@dataclass
class BatchResult:
    processed: list[Path]
    failed: list[tuple[Path, str]]
    cancelled: bool = False


class BatchProcessor:
    """Process a folder of photos without changing the source files."""

    def __init__(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        mode: str = "auto_edit",
        quality: int = 95,
        recursive: bool = False,
        preset=None,
        reference=None,
        recipe: ExportRecipe | None = None,
        input_files: list[str | Path] | None = None,
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.mode = mode
        self.quality = int(max(1, min(100, quality)))
        self.recursive = recursive
        self.preset = preset
        self.reference = reference
        self.recipe = recipe
        self.input_files = [Path(path).expanduser().resolve() for path in input_files] if input_files else None
        self.cancel_event = Event()

    def cancel(self):
        self.cancel_event.set()

    def files(self) -> list[Path]:
        if self.input_files is not None:
            return sorted(
                {path for path in self.input_files if path.is_file() and is_supported(path)},
                key=lambda path: str(path).casefold(),
            )
        iterator = self.input_dir.rglob("*") if self.recursive else self.input_dir.iterdir()
        output_root = self.output_dir.expanduser().resolve()
        input_root = self.input_dir.expanduser().resolve()
        return sorted(
            path for path in iterator
            if path.is_file()
            and is_supported(path)
            and not (
                self.recursive
                and (path.resolve() == output_root or output_root in path.resolve().parents)
            )
            and path.resolve() != input_root
        )

    def _destinations(self, sources: list[Path]) -> list[tuple[Path, Path]]:
        destinations = []
        used: set[Path] = set()
        for source in sources:
            relative = source.relative_to(self.input_dir) if self.recursive else Path(source.name)
            destination = self.output_dir / relative
            if self.recipe is not None:
                destination = destination.with_suffix(self.recipe.extension)
            elif destination.suffix.lower() not in EXPORTABLE_EXTENSIONS:
                destination = destination.with_suffix(".jpg")
            destination = destination.with_name(destination.stem + "_edited" + destination.suffix)
            if destination in used or destination.exists():
                source_tag = source.suffix.lower().lstrip(".") or "source"
                candidate = destination.with_name(
                    f"{destination.stem}_{source_tag}{destination.suffix}"
                )
                destination = candidate
                number = 2
                while destination in used or destination.exists():
                    destination = destination.with_name(
                        f"{candidate.stem}_{number}{candidate.suffix}"
                    )
                    number += 1
            used.add(destination)
            destinations.append((source, destination))
        return destinations

    def _input_profile(self, source: Path) -> str:
        if is_raw(source):
            return "raw"
        suffix = source.suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}:
            return "jpeg" if suffix in {".jpg", ".jpeg"} else suffix.lstrip(".")
        return "generic"

    def _adjustments_for(self, document: Document, source: Path):
        file_kind = self._input_profile(source)
        if self.mode == "auto_edit":
            return auto_edit(document.analysis_image, document.adjustments, file_kind)
        if self.mode == "professional":
            return auto_edit(document.analysis_image, document.adjustments, file_kind)
        if self.mode == "original":
            return document.adjustments
        if self.mode == "auto_grade":
            return auto_colour_grade(document.analysis_image, document.adjustments)
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
        if self.input_dir.expanduser().resolve() == self.output_dir.expanduser().resolve():
            raise ValueError("Choose a separate output folder so your source photos stay untouched.")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        source_files = self.files()
        destinations = dict(self._destinations(source_files))
        processed: list[Path] = []
        failed: list[tuple[Path, str]] = []

        for index, source in enumerate(source_files, 1):
            if self.cancel_event.is_set():
                return BatchResult(processed, failed, True)

            try:
                document = Document()
                document.load(source)
                document.adjustments = self._adjustments_for(document, source)

                destination = destinations[source]
                destination.parent.mkdir(parents=True, exist_ok=True)

                if self.recipe is not None:
                    from core.photo_catalog import export_metadata
                    metadata = (
                        export_metadata(source)
                        if self.recipe.include_metadata else None
                    )
                    export_with_recipe(document.render_master(), destination, self.recipe, metadata)
                else:
                    export_image(
                        document.render_master(),
                        destination,
                        self.quality,
                        icc_profile=srgb_profile_bytes(),
                    )
                processed.append(destination)
            except Exception as exc:
                failed.append((source, str(exc)))

            if progress:
                progress(index, len(source_files), source)

        return BatchResult(processed, failed, False)
