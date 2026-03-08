from pathlib import Path
from typing import List

from .config import SUPPORTED_EXTS
from .settings_store import Settings


class ImageLibrary:
    @staticmethod
    def format_exts_for_label(exts: set[str]) -> str:
        return ", ".join(sorted({ext.lstrip(".").upper() for ext in exts}))

    @staticmethod
    def gtk_patterns_for_exts(exts: set[str]) -> List[str]:
        patterns: List[str] = []
        for ext in exts:
            lower = ext.lower()
            upper = ext.upper()
            patterns.append(f"*{lower}")
            if upper != lower:
                patterns.append(f"*{upper}")
        return patterns

    @staticmethod
    def list_images(folder: Path, recursive: bool) -> List[Path]:
        if not folder.is_dir():
            return []

        exts = {ext.lower() for ext in SUPPORTED_EXTS}
        iterator = folder.rglob("*") if recursive else folder.iterdir()

        images = [
            path for path in iterator
            if path.is_file() and path.suffix.lower() in exts
        ]
        return sorted(images)

    @classmethod
    def effective_selection(cls, settings: Settings) -> List[Path]:
        if settings.use_selected_only and settings.selected:
            valid = [Path(path) for path in settings.selected if Path(path).is_file()]
            if valid:
                return sorted(valid)

        return cls.list_images(Path(settings.folder), settings.recursive)
