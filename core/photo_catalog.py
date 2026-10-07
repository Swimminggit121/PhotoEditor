from __future__ import annotations

import os
import re
import sqlite3
import uuid
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from PIL import ExifTags, Image

from image.loader import is_supported, is_raw, load_preview
from processing.photo_duplicates import collect_photo_paths, find_duplicate_groups


CATALOG_VERSION = 2


def default_catalog_path() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share")
    return root / "PhotoEditor" / "catalog.sqlite3"


@dataclass(frozen=True)
class PhotoRecord:
    id: int
    shoot_id: str
    path: Path
    name: str
    captured_at: str
    camera: str
    lens: str
    width: int
    height: int
    file_size: int
    rating: int
    status: str
    keywords: str
    quality_score: float | None
    quality_notes: str
    duplicate_group: str | None
    missing: bool


@dataclass(frozen=True)
class IndexResult:
    indexed: int
    duplicate_groups: int
    errors: tuple[tuple[Path, str], ...]


def analyze_photo_quality(image: Image.Image) -> tuple[float, tuple[str, ...]]:
    """Return explainable focus/exposure review hints, not an automatic rejection."""
    sample = image.convert("RGB")
    sample.thumbnail((960, 960), Image.Resampling.BILINEAR)
    rgb = np.asarray(sample, dtype=np.uint8)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    luminance = (
        rgb[..., 0].astype(np.float32) * 0.2126
        + rgb[..., 1].astype(np.float32) * 0.7152
        + rgb[..., 2].astype(np.float32) * 0.0722
    ) / 255.0
    underexposed = float(np.mean(luminance < 0.035))
    overexposed = float(np.mean(luminance > 0.985))

    notes = []
    if sharpness < 35:
        notes.append("possible soft focus")
    if underexposed > 0.22:
        notes.append("large area of deep shadows")
    if overexposed > 0.12:
        notes.append("possible clipped highlights")

    focus_score = min(100.0, max(0.0, 100.0 * sharpness / (sharpness + 100.0)))
    exposure_score = max(0.0, 100.0 - 100.0 * min(1.0, underexposed + overexposed))
    score = round(focus_score * 0.55 + exposure_score * 0.45, 1)
    return score, tuple(notes)


def _exif_metadata(path: Path) -> tuple[str, str, str, int, int]:
    if is_raw(path):
        import rawpy

        with rawpy.imread(str(path)) as raw:
            size = raw.sizes
            metadata = raw.metadata
            camera = " ".join(
                str(getattr(metadata, field, "") or "").strip()
                for field in ("make", "model")
            ).strip()
            lens = str(
                getattr(metadata, "lens_model", "")
                or getattr(metadata, "lens", "")
                or ""
            ).strip()
            timestamp = getattr(metadata, "timestamp", None)
            captured = timestamp.isoformat(sep=" ") if isinstance(timestamp, datetime) else ""
            return captured, camera, lens, int(size.width), int(size.height)
    with Image.open(path) as source:
        exif = source.getexif()
        tags = {ExifTags.TAGS.get(key, str(key)): value for key, value in exif.items()}
        try:
            nested = exif.get_ifd(ExifTags.IFD.Exif)
        except (AttributeError, KeyError, TypeError):
            nested = {}
        tags.update({ExifTags.TAGS.get(key, str(key)): value for key, value in nested.items()})
        captured = str(tags.get("DateTimeOriginal") or tags.get("DateTimeDigitized") or tags.get("DateTime") or "")
        if captured:
            try:
                captured = datetime.strptime(captured, "%Y:%m:%d %H:%M:%S").isoformat(sep=" ")
            except ValueError:
                pass
        camera = " ".join(str(tags.get(name, "")).strip() for name in ("Make", "Model")).strip()
        lens = str(tags.get("LensModel") or tags.get("LensSpecification") or "").strip()
        width, height = source.size
        if int(exif.get(274, 1)) in (5, 6, 7, 8):
            width, height = height, width
        return captured, camera, lens, width, height


class PhotoCatalog:
    """A local index of photo paths and review metadata; it never owns source files."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_catalog_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS catalog_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS shoots (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    root_path TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    last_indexed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS photos (
                    id INTEGER PRIMARY KEY,
                    shoot_id TEXT NOT NULL REFERENCES shoots(id) ON DELETE CASCADE,
                    path TEXT NOT NULL,
                    name TEXT NOT NULL,
                    captured_at TEXT NOT NULL DEFAULT '',
                    camera TEXT NOT NULL DEFAULT '',
                    lens TEXT NOT NULL DEFAULT '',
                    width INTEGER NOT NULL DEFAULT 0,
                    height INTEGER NOT NULL DEFAULT 0,
                    file_size INTEGER NOT NULL DEFAULT 0,
                    modified_at REAL NOT NULL DEFAULT 0,
                    rating INTEGER NOT NULL DEFAULT 0 CHECK (rating BETWEEN 0 AND 5),
                    status TEXT NOT NULL DEFAULT 'unreviewed'
                        CHECK (status IN ('unreviewed', 'pick', 'reject')),
                    keywords TEXT NOT NULL DEFAULT '',
                    quality_score REAL,
                    quality_notes TEXT NOT NULL DEFAULT '',
                    duplicate_group TEXT,
                    missing INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(shoot_id, path)
                );
                CREATE INDEX IF NOT EXISTS photos_shoot_capture
                    ON photos(shoot_id, captured_at DESC, name);
                CREATE INDEX IF NOT EXISTS photos_shoot_review
                    ON photos(shoot_id, status, rating DESC);
                CREATE VIRTUAL TABLE IF NOT EXISTS photo_search USING fts5(
                    photo_id UNINDEXED, name, path, camera, lens, captured_at,
                    keywords, quality_notes, tokenize='unicode61'
                );
                """
            )
            existing = connection.execute(
                "SELECT value FROM catalog_meta WHERE key='version'"
            ).fetchone()
            if existing and int(existing["value"]) > CATALOG_VERSION:
                raise RuntimeError(f"Unsupported photo catalog version: {existing['value']}")
            if existing is None or int(existing["value"]) < CATALOG_VERSION:
                connection.execute("DELETE FROM photo_search")
                connection.execute(
                    """
                    INSERT INTO photo_search(
                        photo_id,name,path,camera,lens,captured_at,keywords,quality_notes
                    )
                    SELECT id,name,path,camera,lens,captured_at,keywords,quality_notes FROM photos
                    """
                )
            connection.execute(
                "INSERT OR REPLACE INTO catalog_meta(key, value) VALUES('version', ?)",
                (str(CATALOG_VERSION),),
            )

    def add_shoot(self, folder: str | Path, name: str | None = None) -> str:
        root = Path(folder).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"Choose an existing photo folder: {root}")
        shoot_name = (name or root.name).strip()
        if not shoot_name:
            raise ValueError("A shoot name cannot be empty.")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id FROM shoots WHERE root_path=?", (str(root),)
            ).fetchone()
            if row:
                connection.execute("UPDATE shoots SET name=? WHERE id=?", (shoot_name, row["id"]))
                return str(row["id"])
            shoot_id = uuid.uuid4().hex
            connection.execute(
                "INSERT INTO shoots(id, name, root_path, created_at) VALUES(?,?,?,?)",
                (shoot_id, shoot_name, str(root), datetime.now().isoformat(timespec="seconds")),
            )
            return shoot_id

    def shoots(self) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT s.id, s.name, s.root_path, s.created_at, s.last_indexed_at,
                       COUNT(p.id) AS photo_count,
                       COALESCE(SUM(p.missing), 0) AS missing_count
                FROM shoots s LEFT JOIN photos p ON p.shoot_id=s.id
                GROUP BY s.id ORDER BY s.name COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def shoot(self, shoot_id: str) -> dict:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM shoots WHERE id=?", (shoot_id,)).fetchone()
        if row is None:
            raise ValueError("The selected shoot is no longer in the catalog.")
        return dict(row)

    def index_shoot(
        self,
        shoot_id: str,
        recursive: bool = True,
        progress: Callable[[int, int, Path], None] | None = None,
    ) -> IndexResult:
        shoot = self.shoot(shoot_id)
        root = Path(shoot["root_path"])
        if not root.is_dir():
            with self._connection() as connection:
                connection.execute("UPDATE photos SET missing=1 WHERE shoot_id=?", (shoot_id,))
            raise ValueError("This shoot folder is unavailable. Relink it to continue.")
        photos = collect_photo_paths([root], recursive=recursive)
        errors: list[tuple[Path, str]] = []
        valid_paths: list[Path] = []
        old_rows: dict[str, tuple[float, int, float | None, str]] = {}
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT path, modified_at, file_size, quality_score, quality_notes "
                "FROM photos WHERE shoot_id=?",
                (shoot_id,),
            ).fetchall()
            old_rows = {
                row["path"]: (
                    row["modified_at"], row["file_size"],
                    row["quality_score"], row["quality_notes"],
                )
                for row in rows
            }
            connection.execute("UPDATE photos SET missing=1 WHERE shoot_id=?", (shoot_id,))

        for index, path in enumerate(photos, 1):
            try:
                stat = path.stat()
                captured, camera, lens, width, height = _exif_metadata(path)
                old = old_rows.get(str(path))
                unchanged = old and old[0] == stat.st_mtime and old[1] == stat.st_size and old[2] is not None
                if unchanged:
                    score, notes = old[2], old[3]
                else:
                    image = load_preview(path, max_dimension=960)
                    score, note_list = analyze_photo_quality(image)
                    notes = "; ".join(note_list)
                with self._connection() as connection:
                    connection.execute(
                        """
                        INSERT INTO photos(
                            shoot_id,path,name,captured_at,camera,lens,width,height,file_size,
                            modified_at,quality_score,quality_notes,missing
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,0)
                        ON CONFLICT(shoot_id,path) DO UPDATE SET
                            name=excluded.name, captured_at=excluded.captured_at,
                            camera=excluded.camera, lens=excluded.lens, width=excluded.width,
                            height=excluded.height, file_size=excluded.file_size,
                            modified_at=excluded.modified_at, quality_score=excluded.quality_score,
                            quality_notes=excluded.quality_notes, missing=0
                        """,
                        (
                            shoot_id, str(path), path.name, captured, camera, lens, width, height,
                            stat.st_size, stat.st_mtime, score, notes,
                        ),
                    )
                    row = connection.execute(
                        "SELECT id, name, path, camera, lens, captured_at, keywords, quality_notes "
                        "FROM photos WHERE shoot_id=? AND path=?",
                        (shoot_id, str(path)),
                    ).fetchone()
                    connection.execute(
                        "DELETE FROM photo_search WHERE photo_id=?",
                        (str(row["id"]),),
                    )
                    connection.execute(
                        """
                        INSERT INTO photo_search(
                            photo_id,name,path,camera,lens,captured_at,keywords,quality_notes
                        ) VALUES(?,?,?,?,?,?,?,?)
                        """,
                        tuple(str(row[key] or "") for key in (
                            "id", "name", "path", "camera", "lens",
                            "captured_at", "keywords", "quality_notes",
                        )),
                    )
                valid_paths.append(path)
            except Exception as exc:
                errors.append((path, str(exc)))
            if progress:
                progress(index, len(photos), path)

        duplicate_groups = []
        if len(valid_paths) > 1:
            try:
                if progress:
                    progress(len(photos), max(1, len(photos) * 2), root)
                duplicate_groups = find_duplicate_groups(
                    valid_paths,
                    progress=(
                        lambda current, total, path: progress(
                            len(photos) + current, max(1, len(photos) + total), path
                        )
                    ) if progress else None,
                )
            except Exception as exc:
                errors.append((root, f"Visual duplicate scan could not finish: {exc}"))
        with self._connection() as connection:
            connection.execute("UPDATE photos SET duplicate_group=NULL WHERE shoot_id=?", (shoot_id,))
            for group in duplicate_groups:
                group_id = uuid.uuid4().hex
                connection.executemany(
                    "UPDATE photos SET duplicate_group=? WHERE shoot_id=? AND path=?",
                    [(group_id, shoot_id, str(path)) for path in group.paths],
                )
            connection.execute(
                "UPDATE shoots SET last_indexed_at=? WHERE id=?",
                (datetime.now().isoformat(timespec="seconds"), shoot_id),
            )
        return IndexResult(len(valid_paths), len(duplicate_groups), tuple(errors))

    def photos(
        self,
        shoot_id: str,
        query: str = "",
        status: str = "all",
        issues_only: bool = False,
        sort: str = "newest",
        limit: int = 500,
        offset: int = 0,
    ) -> list[PhotoRecord]:
        if limit <= 0 or offset < 0:
            raise ValueError("Catalog page size must be positive and offset cannot be negative.")
        order_by = {
            "newest": "captured_at DESC, name COLLATE NOCASE",
            "quality": "quality_score DESC, captured_at DESC, name COLLATE NOCASE",
            "warnings": "(quality_notes='' AND duplicate_group IS NULL), quality_score ASC, captured_at DESC",
            "rating": "rating DESC, captured_at DESC, name COLLATE NOCASE",
        }
        if sort not in order_by:
            raise ValueError(f"Unknown catalog sort order: {sort}")
        clauses = ["shoot_id=?"]
        params: list[object] = [shoot_id]
        if query.strip():
            tokens = re.findall(r"[\w]+", query.casefold())
            if tokens:
                match_expression = " AND ".join(f'"{token}"*' for token in tokens)
                clauses.append(
                    "id IN (SELECT CAST(photo_id AS INTEGER) FROM photo_search "
                    "WHERE photo_search MATCH ?)"
                )
                params.append(match_expression)
            else:
                clauses.append("1=0")
        if status != "all":
            clauses.append("status=?")
            params.append(status)
        if issues_only:
            clauses.append("(quality_notes!='' OR duplicate_group IS NOT NULL)")
        sql = (
            "SELECT * FROM photos WHERE " + " AND ".join(clauses)
            + f" ORDER BY {order_by[sort]} LIMIT ? OFFSET ?"
        )
        params.extend((limit, offset))
        with self._connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [
            PhotoRecord(
                id=row["id"], shoot_id=row["shoot_id"], path=Path(row["path"]),
                name=row["name"], captured_at=row["captured_at"], camera=row["camera"],
                lens=row["lens"], width=row["width"], height=row["height"],
                file_size=row["file_size"], rating=row["rating"], status=row["status"],
                keywords=row["keywords"], quality_score=row["quality_score"],
                quality_notes=row["quality_notes"], duplicate_group=row["duplicate_group"],
                missing=bool(row["missing"]),
            )
            for row in rows
        ]

    def update_photo(
        self,
        photo_id: int,
        *,
        rating: int | None = None,
        status: str | None = None,
        keywords: str | None = None,
    ) -> None:
        updates = {}
        if rating is not None:
            if not 0 <= rating <= 5:
                raise ValueError("Ratings must be between zero and five stars.")
            updates["rating"] = rating
        if status is not None:
            if status not in {"unreviewed", "pick", "reject"}:
                raise ValueError("Photo status must be unreviewed, pick, or reject.")
            updates["status"] = status
        if keywords is not None:
            updates["keywords"] = ", ".join(
                dict.fromkeys(term.strip() for term in keywords.split(",") if term.strip())
            )
        if not updates:
            return
        clause = ", ".join(f"{key}=?" for key in updates)
        with self._connection() as connection:
            cursor = connection.execute(
                f"UPDATE photos SET {clause} WHERE id=?",
                (*updates.values(), photo_id),
            )
            if keywords is not None and cursor.rowcount:
                row = connection.execute(
                    "SELECT id,name,path,camera,lens,captured_at,keywords,quality_notes "
                    "FROM photos WHERE id=?",
                    (photo_id,),
                ).fetchone()
                connection.execute("DELETE FROM photo_search WHERE photo_id=?", (str(photo_id),))
                connection.execute(
                    """
                    INSERT INTO photo_search(
                        photo_id,name,path,camera,lens,captured_at,keywords,quality_notes
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    tuple(str(row[key] or "") for key in (
                        "id", "name", "path", "camera", "lens",
                        "captured_at", "keywords", "quality_notes",
                    )),
                )
        if cursor.rowcount == 0:
            raise ValueError("The selected photo is no longer in the catalog.")

    def relink_shoot(self, shoot_id: str, folder: str | Path) -> None:
        new_root = Path(folder).expanduser().resolve()
        if not new_root.is_dir():
            raise ValueError(f"Choose an existing folder to relink: {new_root}")
        shoot = self.shoot(shoot_id)
        old_root = Path(shoot["root_path"])
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, path FROM photos WHERE shoot_id=?", (shoot_id,)
            ).fetchall()
            connection.execute(
                "UPDATE shoots SET root_path=?, name=? WHERE id=?",
                (str(new_root), new_root.name, shoot_id),
            )
            connection.execute("UPDATE photos SET missing=1 WHERE shoot_id=?", (shoot_id,))
            for row in rows:
                old_path = Path(row["path"])
                try:
                    relative = old_path.relative_to(old_root)
                except ValueError:
                    relative = Path(old_path.name)
                candidate = new_root / relative
                if candidate.is_file() and is_supported(candidate):
                    connection.execute(
                        "UPDATE photos SET path=?, name=?, missing=0 WHERE id=?",
                        (str(candidate.resolve()), candidate.name, row["id"]),
                    )
            connection.execute(
                "DELETE FROM photo_search WHERE photo_id IN "
                "(SELECT CAST(id AS TEXT) FROM photos WHERE shoot_id=?)",
                (shoot_id,),
            )
            connection.execute(
                """
                INSERT INTO photo_search(
                    photo_id,name,path,camera,lens,captured_at,keywords,quality_notes
                )
                SELECT CAST(id AS TEXT),name,path,camera,lens,captured_at,keywords,quality_notes
                FROM photos WHERE shoot_id=?
                """,
                (shoot_id,),
            )

    def backup(self, target: str | Path) -> Path:
        backup_path = Path(target).expanduser()
        if backup_path.resolve() == self.path.resolve():
            raise ValueError("Choose a different file for the catalog backup.")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = backup_path.with_name(f".{backup_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with self._connection() as source, closing(sqlite3.connect(temporary)) as destination:
                source.backup(destination)
                if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("The catalog backup did not pass its integrity check.")
                destination.commit()
            temporary.replace(backup_path)
        finally:
            temporary.unlink(missing_ok=True)
        return backup_path

    def restore(self, backup: str | Path) -> None:
        backup_path = Path(backup).expanduser()
        if not backup_path.is_file():
            raise ValueError(f"Catalog backup not found: {backup_path}")
        if backup_path.resolve() == self.path.resolve():
            raise ValueError("Choose a backup file other than the active catalog.")
        with closing(sqlite3.connect(backup_path)) as connection:
            version = connection.execute(
                "SELECT value FROM catalog_meta WHERE key='version'"
            ).fetchone()
            if version is None or int(version[0]) != CATALOG_VERSION:
                raise ValueError("This is not a compatible PhotoEditor catalog backup.")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("The selected catalog backup failed its integrity check.")
        with closing(sqlite3.connect(backup_path)) as source, self._connection() as destination:
            source.backup(destination)


def export_metadata(path: str | Path) -> bytes | None:
    source_path = Path(path)
    if source_path.suffix.casefold() in {
        ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".dng",
        ".raf", ".orf", ".rw2", ".pef", ".srw", ".3fr", ".iiq", ".rwl",
        ".raw", ".dcr", ".kdc", ".mrw", ".x3f", ".erf", ".mef", ".mos", ".fff",
    }:
        return None
    with Image.open(source_path) as image:
        exif = image.getexif()
        if not exif:
            return None
        exif[274] = 1
        return exif.tobytes()
